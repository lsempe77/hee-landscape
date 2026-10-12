"""Check review-versus-input distinctions and safe joins on synthetic records."""

import importlib.util
from pathlib import Path
import unittest

spec = importlib.util.spec_from_file_location('review_screen', Path(__file__).resolve().parents[1] / 'scripts' / 'screen_reviews_with_abstracts.py')
screen = importlib.util.module_from_spec(spec)
spec.loader.exec_module(screen)


class ReviewScreenTests(unittest.TestCase):
    def test_explicit_systematic_review(self):
        r = screen.classify('Costs of diabetes care: a systematic review', 'We conducted a systematic review. We searched PubMed. Twenty studies were included.')
        self.assertEqual(r['review_type'], 'Systematic review')

    def test_model_using_review_is_not_review_paper(self):
        r = screen.classify('Cost-effectiveness of vaccination', 'We developed a Markov model. Inputs were obtained from a systematic review of trials.')
        self.assertEqual(r['review_type'], 'No review identified')
        self.assertTrue(r['review_component'])

    def test_scoping_review_is_not_assumed_nonsystematic(self):
        self.assertEqual(screen.classify('A scoping review of health costs', '')['review_type'], 'Other review - methods need checking')

    def test_narrative_review(self):
        self.assertEqual(screen.classify('A narrative review of costs', '')['review_type'], 'Non-systematic review')

    def test_registry_analysis(self):
        r = screen.classify('An economic evaluation using registry data', 'We used patient registry data to compare costs and outcomes.')
        self.assertEqual(r['review_type'], 'No review identified')

    def test_background_reference_does_not_establish_review(self):
        r = screen.classify('Costs of treatment', 'An earlier systematic review found insufficient evidence. We assessed costs in a patient cohort.')
        self.assertEqual(r['review_type'], 'Unclear - manual check needed')

    def test_hybrid_kept_separate(self):
        r = screen.classify('Systematic review and model-based evaluation', 'We conducted a systematic review. We developed a Markov model.')
        self.assertEqual(r['review_type'], 'Mixed review and original evaluation')
        self.assertEqual(r['review_mixed_primary_analysis'], 'TRUE')

    def test_meta_analysis_alone_is_not_proof_of_systematic_methods(self):
        self.assertEqual(screen.classify('A meta-analysis of treatment costs', '')['review_type'], 'Other review - methods need checking')

    def test_protocol_is_not_completed_review(self):
        self.assertEqual(screen.classify('Protocol for a systematic review of costs', '')['review_type'], 'Review protocol')

    def test_chart_review_is_not_literature_review(self):
        self.assertEqual(screen.classify('A retrospective chart review of costs', '')['review_type'], 'No review identified')

    def test_review_of_trials_is_not_itself_a_trial(self):
        r = screen.classify('A systematic review of trial-based studies', 'We conducted a systematic review of randomized controlled trials.')
        self.assertEqual(r['review_type'], 'Systematic review')

    def test_review_of_treatment_protocol_is_not_review_protocol(self):
        r = screen.classify('ERAS protocol: a systematic review', 'We searched PubMed and included ten studies.')
        self.assertEqual(r['review_type'], 'Systematic review')

    def test_review_of_cost_effectiveness_is_not_new_evaluation(self):
        r = screen.classify('A systematic review', 'We conducted a systematic review on cost-effectiveness of treatment.')
        self.assertEqual(r['review_type'], 'Systematic review')

    def test_new_cohort_and_review_kept_mixed(self):
        r = screen.classify('Treatment costs and a narrative review', 'In this cross-sectional study, we assessed twelve patients.')
        self.assertEqual(r['review_type'], 'Mixed review and original evaluation')

    def test_appraisal_group_does_not_establish_review_paper(self):
        r = screen.classify('An Evidence Review Group Perspective of a NICE Single Technology Appraisal', 'The model was validated.')
        self.assertEqual(r['review_type'], 'Unclear - manual check needed')


if __name__ == '__main__':
    unittest.main()
