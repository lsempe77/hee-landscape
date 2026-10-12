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

    def test_scoping_review_uses_user_operational_category(self):
        r = screen.classify('A scoping review of health costs', '')
        self.assertEqual(r['review_type'], 'Non-systematic review')
        self.assertIn('does not establish', r['review_screen_reason'])

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
        self.assertEqual(screen.classify('A meta-analysis of treatment costs', '')['review_type'], 'Non-systematic review')

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

    def test_title_says_review_data_are_model_input(self):
        r = screen.classify('Cost savings: an economic model based on data from a systematic review', 'A Markov model was developed.')
        self.assertEqual(r['review_type'], 'No review identified')

    def test_mixed_methods_with_narrative_review(self):
        r = screen.classify('Mixed-methods analysis', 'We conducted a mixed-methods analysis integrating a narrative review and an economic evaluation.')
        self.assertEqual(r['review_type'], 'Mixed review and original evaluation')

    def test_other_title_with_explicit_sr_abstract(self):
        r = screen.classify('A literature review of health costs', 'We conducted a systematic review of economic evaluations.')
        self.assertEqual(r['review_type'], 'Systematic review')

    def test_methods_alone_follow_explicit_label_policy(self):
        r = screen.classify('Costs of treatment: a review', 'We searched PubMed using a systematic search. Ten studies were included and quality assessment was performed.')
        self.assertEqual(r['review_type'], 'Non-systematic review')

    def test_meta_analysis_not_performed(self):
        r = screen.classify('A systematic review of costs', 'Narrative synthesis, rather than a formal meta-analysis, was undertaken.')
        self.assertEqual(r['review_subtype'], 'Systematic review without meta-analysis')

    def test_purpose_explicitly_identifies_systematic_review(self):
        r = screen.classify('Economic evidence for treatment', 'The present study aims to compare the treatments through a systematic literature review and meta-analysis.')
        self.assertEqual(r['review_type'], 'Systematic review')

    def test_review_and_parameters_in_new_model(self):
        r = screen.classify('Model parameters for treatment costs', 'A systematic review was performed. The parameters were incorporated into a cost-utility model.')
        self.assertEqual(r['review_type'], 'Mixed review and original evaluation')

    def test_own_meta_analysis_with_reimbursement_analysis(self):
        r = screen.classify('Treatment outcomes and economic costs', 'We performed meta-analyses of efficacy. We analyzed individual reimbursement data from insurance records.')
        self.assertEqual(r['review_type'], 'Mixed review and original evaluation')

    def test_systemised_review_with_new_scenarios(self):
        r = screen.classify('A systemised review and modelling study', 'We undertook a systemised review of taxes. These tax scenarios were modelled to estimate lifetime costs.')
        self.assertEqual(r['review_type'], 'Mixed review and original evaluation')

    def test_drug_utilization_review_is_service(self):
        r = screen.classify('Costs of drug utilization review', 'We conducted difference-in-differences analysis using insurance claims data.')
        self.assertEqual(r['review_type'], 'No review identified')

    def test_title_identifies_review_and_new_model(self):
        r = screen.classify('Treatment: a systematic review and economic evaluation', 'A decision-analytic model was developed. Inputs were informed by a systematic review.')
        self.assertEqual(r['review_type'], 'Mixed review and original evaluation')

    def test_prior_guideline_reviews_are_inputs(self):
        r = screen.classify('Cost-effectiveness of brief advice', 'A Markov model was used. Data to populate the model were derived from systematic literature reviews and literature searches that were conducted for national guidelines.')
        self.assertEqual(r['review_type'], 'No review identified')


if __name__ == '__main__':
    unittest.main()
