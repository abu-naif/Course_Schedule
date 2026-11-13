"""Check the optimized search against exhaustive enumeration, without network access."""
import itertools
import random
import tempfile
import unittest
from datetime import date
from unittest.mock import patch

import app as web
import prepreg_scraper as ps
import schedule_combinator as sc


def row(code, section, meetings, faculty='ABC', exam=None):
    return {'course_code':code,'sectionName':str(section),'faculty':faculty,
            'all_meetings':meetings,'theory_meetings':meetings[:1], 'lab_meetings':meetings[1:],
            'capacity':30,'consumedSeat':10,'remaining':20,
            'exam':exam or {'parsed':False,'raw':'TBA'}}


def meeting(day, start, end):
    return ps.Meeting(day,start,end,str(start),str(end),'101')


def identities(combos):
    return [tuple((r['course_code'],r['sectionName']) for r in combo) for combo in combos]


class ExactSearchTests(unittest.TestCase):
    def test_matches_exhaustive_search_and_stable_ties(self):
        rng=random.Random(171)
        prefs=sc.parse_faculty_preferences(['ABC','C1:XYZ'])
        for seed in range(75):
            groups=[]
            for course in range(rng.randint(2,4)):
                rows=[]
                for section in range(rng.randint(1,4)):
                    meetings=[]
                    for _ in range(rng.randint(0,3)):
                        start=rng.choice([480,540,600,660])
                        meetings.append(meeting(rng.choice(['SUNDAY','MONDAY','THURSDAY']),start,start+rng.choice([60,80,120])))
                    exam={'parsed':rng.choice([False,True]),'date':date(2027,1,rng.choice([1,2])),
                          'start':rng.choice([480,540,600]),'end':680,'raw':'Sample'}
                    rows.append(row(f'C{course}',section,meetings,rng.choice(['ABC','XYZ','TBA']),exam))
                groups.append(rows)
            for sorting in ['none','days','faculty,days','gap,faculty','target_days,gap','earliest,latest','latest,days']:
                for exact,target in [(False,None),(False,2),(True,1),(True,2),(True,3)]:
                    with self.subTest(seed=seed,sorting=sorting,exact=exact,target=target):
                        key,keys=sc.build_sort_key_fn(sorting,prefs,target_days=target,on_warning=lambda _:None)
                        expected=[combo for combo in itertools.product(*groups)
                                  if sc.is_valid_combo(combo) and (not exact or sc.days_used_score(combo)==target)]
                        if keys!=['none']: expected.sort(key=key)
                        total,retained=sc.search_combinations(groups,keys,prefs,target_days=target,exact_days=exact,max_results=5)
                        self.assertEqual(total,len(expected))
                        self.assertEqual(identities([x[0] for x in retained]),identities(expected[:5]))
                        for combo,stats,rank in retained:
                            self.assertEqual(rank,key(combo))
                            self.assertEqual(stats['gap'],sc.gap_score(combo))
                            self.assertEqual(stats['days'],sc.days_used_score(combo))
                            self.assertEqual(stats['faculty_matches'],sc.faculty_match_count(combo,prefs))

    def test_counts_beyond_previous_web_limit(self):
        groups=[[row(f'C{i}',j,[]) for j in range(7)] for i in range(6)]
        prefs=sc.parse_faculty_preferences(None)
        total,results=sc.search_combinations(groups,['none'],prefs,max_results=3)
        self.assertEqual(total,7**6)
        self.assertEqual(identities([r[0] for r in results]),identities(list(itertools.islice(itertools.product(*groups),3))))

    def test_exact_counting_can_skip_noncompetitive_trillion_combination_branch(self):
        groups=[[row(f'C{i}',j,[]) for j in range(10)] for i in range(12)]
        total,results=sc.search_combinations(groups,['none'],sc.parse_faculty_preferences(None),max_results=3)
        self.assertEqual(total,10**12)
        self.assertEqual(identities([r[0] for r in results]),identities(list(itertools.islice(itertools.product(*groups),3))))

    def test_touching_times_allowed_and_overlapping_labs_and_exams_rejected(self):
        prefs=sc.parse_faculty_preferences(None)
        first=row('A',1,[meeting('SUNDAY',480,540),meeting('MONDAY',600,720)],exam={'parsed':True,'date':date(2027,1,1),'start':480,'end':540})
        groups=[[first],[row('B',1,[meeting('SUNDAY',540,600)]),
                         row('B',2,[meeting('MONDAY',660,740)]),
                         row('B',3,[],exam={'parsed':True,'date':date(2027,1,1),'start':500,'end':560})]]
        total,results=sc.search_combinations(groups,['days'],prefs)
        self.assertEqual(total,1)
        self.assertEqual(results[0][0][1]['sectionName'],'1')

    def test_cache_invalidates_when_feed_or_preferences_change(self):
        cache=web.ExactAnalysisCache(capacity=2)
        feed1={'courses':[]};feed2={'courses':[]}
        self.assertIsNone(cache.get(feed1,'a'))
        cache.put(feed1,'a',{'answer':1})
        self.assertEqual(cache.get(feed1,'a'),{'answer':1})
        self.assertIsNone(cache.get(feed1,'b'))
        self.assertIsNone(cache.get(feed2,'a'))
        cache.put(feed1,'a',{'answer':'old request finishing late'})
        self.assertIsNone(cache.get(feed2,'a'))
        for key in ['a','b','c']:cache.put(feed2,key,{'answer':key})
        self.assertIsNone(cache.get(feed2,'a'))
        self.assertEqual(cache.get(feed2,'c'),{'answer':'c'})

    def test_web_and_csv_use_the_same_exact_results(self):
        feed={'courses':[{'courseCode':code,'sectionName':str(section),'faculties':faculty,'capacity':30,'consumedSeat':5,
                          'sectionSchedule':{'classSchedules':[{'day':day,'startTime':start,'endTime':end}]}}
                         for code,section,faculty,day,start,end in [
                             ('CSE110',1,'ABC','SUNDAY','08:00:00','09:20:00'),
                             ('CSE110',2,'XYZ','MONDAY','09:30:00','10:50:00'),
                             ('MAT110',1,'ABC','SUNDAY','08:00:00','09:20:00'),
                             ('MAT110',2,'ABC','MONDAY','11:00:00','12:20:00')]]}
        request=web.GenerateRequest(courses=['CSE110','MAT110'],prefer_faculty=['ABC'],sort_by='faculty',secondary_sort_by='days')
        with patch.object(web.cache,'get_feed',return_value=feed):
            result=web.generate_schedules(request)
            cached=web.generate_schedules(request)
        self.assertEqual(result['total_valid'],3)
        self.assertEqual(result['combinations'],cached['combinations'])
        self.assertIn('Reused an identical analysis',cached['logs'][-1])
        with tempfile.TemporaryDirectory() as output,patch.object(sc,'fetch_feed',return_value=feed),patch.object(sc,'write_csv') as write:
            exported=sc.run_combinator(courses=request.courses,prefer_faculty=request.prefer_faculty,sort_by='faculty,days',output_format='csv',output_dir=output,log=lambda _:None)
            self.assertEqual(exported['total_valid'],result['total_valid'])
            rows=write.call_args.args[0]
            self.assertEqual(identities([x[0] for x in rows]),[tuple((s['courseCode'],s['sectionName']) for s in c['sections']) for c in result['combinations']])

    def test_web_constraints_remain_hard_filters(self):
        feed={'courses':[
            {'courseCode':code,'sectionName':section,'faculties':faculty,
             'capacity':30,'consumedSeat':5,'sectionSchedule':{'classSchedules':[
                 {'day':day,'startTime':start,'endTime':end}]}}
            for code,section,faculty,day,start,end in [
                ('CSE110','01','ABC','SUNDAY','08:00:00','09:20:00'),
                ('CSE110','02','XYZ','MONDAY','09:30:00','10:50:00'),
                ('MAT110','01','ABC','SUNDAY','08:00:00','09:20:00'),
                ('MAT110','02','ABC','MONDAY','11:00:00','12:20:00')]]}
        request=web.GenerateRequest(
            courses=['CSE110','MAT110'],only_open=True,
            mandatory_sections=['CSE110:02'],prefer_faculty=['CSE110:XYZ','MAT110:ABC'],
            avoid_faculty=['CSE110:ABC'],mandatory_preferred_faculty=True,
            skip_times=['Sun 08:00 AM - 09:20 AM'],target_days=1,exact_days=True)
        with patch.object(web.cache,'get_feed',return_value=feed):
            result=web.generate_schedules(request)
        self.assertEqual(result['total_valid'],1)
        self.assertEqual([s['sectionName'] for s in result['combinations'][0]['sections']],['02','02'])
        self.assertEqual(result['combinations'][0]['stats']['days'],1)
        request.target_days=7
        with patch.object(web.cache,'get_feed',return_value=feed):
            empty=web.generate_schedules(request)
            cached=web.generate_schedules(request)
        self.assertEqual(empty['total_valid'],0)
        self.assertEqual(cached['total_valid'],0)
        self.assertIn('Reused an identical analysis',cached['logs'][-1])


if __name__=='__main__':unittest.main()
