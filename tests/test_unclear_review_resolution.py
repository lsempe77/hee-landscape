"""Guard the agreed distinction between own reviews and review inputs."""
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import resolve_unclear_reviews as resolution


class ResolutionTests(unittest.TestCase):
    def assess(self, abstract, title='Economic evaluation'):
        return resolution.propose({'record_id': 'synthetic', 'title': title, 'abstract': abstract})

    def test_own_systematic_review_and_model(self):
        result = self.assess('We conducted a systematic review. We developed a Markov model to compare costs.')
        self.assertEqual(result['review_type'], 'Systematic review')
        self.assertEqual(result['review_has_original_evaluation'], 'Yes')

    def test_unattributed_review_input_stays_uncertain(self):
        self.assertIsNone(self.assess('We developed a Markov model. Probabilities were obtained from a systematic review.'))

    def test_named_prior_review_is_input(self):
        result = self.assess('We developed a Markov model. Data came from a previously published systematic review.')
        self.assertEqual(result['review_type'], 'Not identified as a review')

    def test_scoping_review_of_systematic_reviews(self):
        result = self.assess('Methods: A cohort model was informed by a scoping review of systematic reviews.', 'Cost modelling')
        self.assertEqual(result['review_type'], 'Review (non-systematic)')

    def test_cohort_input_cannot_establish_own_review(self):
        self.assertIsNone(self.assess('Methods: A hypothetical cohort was evaluated using a Markov model incorporating data from systematic reviews of test accuracy.'))

    def test_rapid_search_is_not_explicit_own_systematic_review(self):
        result = self.assess('Databases were searched to retrieve published systematic reviews. Five studies were included.', 'Rapid health technology assessment')
        self.assertEqual(result['review_type'], 'Review (non-systematic)')

    def test_patient_chart_review_is_not_synthesis(self):
        result = self.assess('We conducted a retrospective review of medical records to compare costs.', 'Review of patient records')
        self.assertEqual(result['review_type'], 'Not identified as a review')


if __name__ == '__main__':
    unittest.main()
