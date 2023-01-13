from collections import Counter
from typing import Any
import requests
from pathlib import Path
import random
import json
import time
from enum import Enum
from nltk.util import everygrams

# THIS SCRIPT EVALUATES ACCURACY AND GLEU SCORES FOR A TRAINED MODEL
# PLEASE SET THE FOLLOWING VARIABLES
# 1. API_TOKEN (retrieve from the support portal @ https://support.lumina247.com)
# 2. SET SESSION_KEY this is the session_key for your trained model
# 3. SET THE Revision number for the showcase model
# 4. SET TEST_PATH this is a path to your test data
# 5. SET GLEU_ITERATION_COUNT this is the total number of iterations gleu score will be evaluated
# 6. SET GLEU_EVALUATION_SAMPLE_SIZE this is the total sample size for each gleu iteration

API_URL = "https://rclapi.lumina247.io"

# 1 example: bearer <token>
API_TOKEN = "bearer eyJraWQiOiJpZzA2bDFkQjhlQkUxanAxN0tkYTMxUlVNVEM4QVpVdXVFVGd4aHQ1ZWQ0PSIsImFsZyI6IlJTMjU2In0.eyJzdWIiOiI4YWI3MzUxOC1mYjhhLTQ1YmUtYmEzNC0wMzYxYjdkYzNjMTYiLCJpc3MiOiJodHRwczpcL1wvY29nbml0by1pZHAudXMtZWFzdC0xLmFtYXpvbmF3cy5jb21cL3VzLWVhc3QtMV9zYkNlc1k5eWMiLCJ2ZXJzaW9uIjoyLCJjbGllbnRfaWQiOiIzcDM2c2xsZTc1ZjYzcXJpMHRhczZldG9zNSIsIm9yaWdpbl9qdGkiOiIwMmI5YjRlNS1lNzFlLTQyNTctOWZmYS1kNDFiMDhmMzU1M2EiLCJldmVudF9pZCI6IjMwNmZmNmYzLWIxYWYtNDc5ZS1hMDQ1LWQzOWY2MmFmZjA1ZSIsInRva2VuX3VzZSI6ImFjY2VzcyIsInNjb3BlIjoib3BlbmlkIHByb2ZpbGUiLCJhdXRoX3RpbWUiOjE2NzM2Mjg1OTcsImV4cCI6MTY3MzcxNTAwMCwiaWF0IjoxNjczNjI4NjAwLCJqdGkiOiI0ODYyNDU5MS01N2Y2LTQ0MzEtYjkxZC01OThkODRlODllNmIiLCJ1c2VybmFtZSI6IjhhYjczNTE4LWZiOGEtNDViZS1iYTM0LTAzNjFiN2RjM2MxNiJ9.Zd3Htc6XdyM9UFQ2YcrKbdYHaXPwkNObHWbTnT371AzE_ZUfFd_5GOur26SpP1aFK_77bKY1B1uHuT9GVnYDFHShu7lY4KJ-0mMWD9Jekorq2477W3HiaxAdeRS0NIETIcda9PFAhJca7-VcjxDFw0dHuaz8gUtr7sGF-7-8SNTZzJ5TdeZMq4MdogV_akOxoJuvmp2xabCFmxxcbBwdZBkWeiNaRAb_Kwrkovo04O92FmTPnizhTMtsmhYov5aTK98wZ6VJg_EWc4WboWBbwW24LVf_RgGvw13Lekfe-bw8asFZSTPIGtdROyqA9agi_erlvzIwiY_iV1DFx9uegw"

# 2 SET TRAINING SESSION KEY HERE
SESSION_KEY = "127758762"

REVISION_NUMBER = "1"

# 3
# SET TEST DATA PATH HERE
# DANISH
TEST_PATH = "example_data/tatoeba/danish/test_data/test_data_Cleansed_r.txt"

# 4 
# SET GLEU EVALUATION ITERATION COUNT
GLEU_ITERATION_COUNT = 5

# 5
# SET GLEU EVALUATION SAMPLE SIZE
GLEU_EVALUATION_SAMPLE_SIZE = 1000

HEADERS = {
    "Content-type": "application/json",
    "Accept": "application/json",
    "Authorization": API_TOKEN,
}

class InferenceDetailType(Enum):
    """Enums containing the id's for inference types"""
    search = "Search"
    predict_line = "PredictLine"
    predict_next = "PredictNext"
    translate_line = "TranslateLine"
    hot_word = "HotWord"

class InferencePriorityType(Enum):
    """Enums containing the id's for training optimizers"""
    index = "Index"
    accuracy = "Accuracy"
    specific = "Specific"

def sentence_gleu(references, hypothesis, min_len=1, max_len=4):
    """
    Calculates the sentence level GLEU (Google-BLEU) score described in

        Yonghui Wu, Mike Schuster, Zhifeng Chen, Quoc V. Le, Mohammad Norouzi,
        Wolfgang Macherey, Maxim Krikun, Yuan Cao, Qin Gao, Klaus Macherey,
        Jeff Klingner, Apurva Shah, Melvin Johnson, Xiaobing Liu, Lukasz Kaiser,
        Stephan Gouws, Yoshikiyo Kato, Taku Kudo, Hideto Kazawa, Keith Stevens,
        George Kurian, Nishant Patil, Wei Wang, Cliff Young, Jason Smith,
        Jason Riesa, Alex Rudnick, Oriol Vinyals, Greg Corrado, Macduff Hughes,
        Jeffrey Dean. (2016) Google’s Neural Machine Translation System:
        Bridging the Gap between Human and Machine Translation.
        eprint arXiv:1609.08144. https://arxiv.org/pdf/1609.08144v2.pdf
        Retrieved on 27 Oct 2016.

    From Wu et al. (2016):
        "The BLEU score has some undesirable properties when used for single
         sentences, as it was designed to be a corpus measure. We therefore
         use a slightly different score for our RL experiments which we call
         the 'GLEU score'. For the GLEU score, we record all sub-sequences of
         1, 2, 3 or 4 tokens in output and target sequence (n-grams). We then
         compute a recall, which is the ratio of the number of matching n-grams
         to the number of total n-grams in the target (ground truth) sequence,
         and a precision, which is the ratio of the number of matching n-grams
         to the number of total n-grams in the generated output sequence. Then
         GLEU score is simply the minimum of recall and precision. This GLEU
         score's range is always between 0 (no matches) and 1 (all match) and
         it is symmetrical when switching output and target. According to
         our experiments, GLEU score correlates quite well with the BLEU
         metric on a corpus level but does not have its drawbacks for our per
         sentence reward objective."

    Note: The initial implementation only allowed a single reference, but now
          a list of references is required (which is consistent with
          bleu_score.sentence_bleu()).

    The infamous "the the the ... " example

        >>> ref = 'the cat is on the mat'.split()
        >>> hyp = 'the the the the the the the'.split()
        >>> sentence_gleu([ref], hyp)  # doctest: +ELLIPSIS
        0.0909...

    An example to evaluate normal machine translation outputs

        >>> ref1 = str('It is a guide to action that ensures that the military '
        ...            'will forever heed Party commands').split()
        >>> hyp1 = str('It is a guide to action which ensures that the military '
        ...            'always obeys the commands of the party').split()
        >>> hyp2 = str('It is to insure the troops forever hearing the activity '
        ...            'guidebook that party direct').split()
        >>> sentence_gleu([ref1], hyp1) # doctest: +ELLIPSIS
        0.4393...
        >>> sentence_gleu([ref1], hyp2) # doctest: +ELLIPSIS
        0.1206...

    :param references: a list of reference sentences
    :type references: list(list(str))
    :param hypothesis: a hypothesis sentence
    :type hypothesis: list(str)
    :param min_len: The minimum order of n-gram this function should extract.
    :type min_len: int
    :param max_len: The maximum order of n-gram this function should extract.
    :type max_len: int
    :return: the sentence level GLEU score.
    :rtype: float
    """
    result = corpus_gleu([references], [hypothesis], min_len=min_len, max_len=max_len)
    return result

def corpus_gleu(list_of_references, hypotheses, min_len, max_len):
    """
    Calculate a single corpus-level GLEU score (aka. system-level GLEU) for all
    the hypotheses and their respective references.

    Instead of averaging the sentence level GLEU scores (i.e. macro-average
    precision), Wu et al. (2016) sum up the matching tokens and the max of
    hypothesis and reference tokens for each sentence, then compute using the
    aggregate values.

    From Mike Schuster (via email):
        "For the corpus, we just add up the two statistics n_match and
         n_all = max(n_all_output, n_all_target) for all sentences, then
         calculate gleu_score = n_match / n_all, so it is not just a mean of
         the sentence gleu scores (in our case, longer sentences count more,
         which I think makes sense as they are more difficult to translate)."

    >>> hyp1 = ['It', 'is', 'a', 'guide', 'to', 'action', 'which',
    ...         'ensures', 'that', 'the', 'military', 'always',
    ...         'obeys', 'the', 'commands', 'of', 'the', 'party']
    >>> ref1a = ['It', 'is', 'a', 'guide', 'to', 'action', 'that',
    ...          'ensures', 'that', 'the', 'military', 'will', 'forever',
    ...          'heed', 'Party', 'commands']
    >>> ref1b = ['It', 'is', 'the', 'guiding', 'principle', 'which',
    ...          'guarantees', 'the', 'military', 'forces', 'always',
    ...          'being', 'under', 'the', 'command', 'of', 'the', 'Party']
    >>> ref1c = ['It', 'is', 'the', 'practical', 'guide', 'for', 'the',
    ...          'army', 'always', 'to', 'heed', 'the', 'directions',
    ...          'of', 'the', 'party']

    >>> hyp2 = ['he', 'read', 'the', 'book', 'because', 'he', 'was',
    ...         'interested', 'in', 'world', 'history']
    >>> ref2a = ['he', 'was', 'interested', 'in', 'world', 'history',
    ...          'because', 'he', 'read', 'the', 'book']

    >>> list_of_references = [[ref1a, ref1b, ref1c], [ref2a]]
    >>> hypotheses = [hyp1, hyp2]
    >>> corpus_gleu(list_of_references, hypotheses) # doctest: +ELLIPSIS
    0.5673...

    The example below show that corpus_gleu() is different from averaging
    sentence_gleu() for hypotheses

    >>> score1 = sentence_gleu([ref1a], hyp1)
    >>> score2 = sentence_gleu([ref2a], hyp2)
    >>> (score1 + score2) / 2 # doctest: +ELLIPSIS
    0.6144...

    :param list_of_references: a list of reference sentences, w.r.t. hypotheses
    :type list_of_references: list(list(list(str)))
    :param hypotheses: a list of hypothesis sentences
    :type hypotheses: list(list(str))
    :param min_len: The minimum order of n-gram this function should extract.
    :type min_len: int
    :param max_len: The maximum order of n-gram this function should extract.
    :type max_len: int
    :return: The corpus-level GLEU score.
    :rtype: float
    """
    # sanity check
    assert len(list_of_references) == len(
        hypotheses
    ), "The number of hypotheses and their reference(s) should be the same"

    # sum matches and max-token-lengths over all sentences
    corpus_n_match = 0
    corpus_n_all = 0

    for references, hypothesis in zip(list_of_references, hypotheses):
        hyp_ngrams = Counter(everygrams(hypothesis, min_len, max_len))
        tpfp = sum(hyp_ngrams.values())  # True positives + False positives.

        hyp_counts = []
        for reference in references:
            ref_ngrams = Counter(everygrams(reference, min_len, max_len))
            # True positives + False negatives.
            tpfn = sum(ref_ngrams.values())

            overlap_ngrams = ref_ngrams & hyp_ngrams
            tp = sum(overlap_ngrams.values())  # True positives.

            # While GLEU is defined as the minimum of precision and
            # recall, we can reduce the number of division operations by one by
            # instead finding the maximum of the denominators for the precision
            # and recall formulae, since the numerators are the same:
            #     precision = tp / tpfp
            #     recall = tp / tpfn
            #     gleu_score = min(precision, recall) == tp / max(tpfp, tpfn)
            n_all = max(tpfp, tpfn)

            if n_all > 0:
                hyp_counts.append((tp, n_all))

        # use the reference yielding the highest score
        if hyp_counts:
            n_match, n_all = max(hyp_counts, key=lambda hc: hc[0] / hc[1])
            corpus_n_match += n_match
            corpus_n_all += n_all

    # corner case: empty corpus or empty references---don't divide by zero!
    if corpus_n_all == 0:
        gleu_score = 0.0
    else:
        gleu_score = corpus_n_match / corpus_n_all

    return gleu_score

def parse_api_response(response: requests.Response) -> dict[str, Any]:
    """extracts json from response and raises errors when needed"""
    if response.status_code > 200:
        raise Exception("Error calling api")
    return {k.lower(): v for k, v in response.json().items()}

def sample_translation_set(path: Path):
    keep = []
    
    lines = path.read_text(encoding="utf-8").strip().split("\n")
    
    for l in lines:
        en, xx = l.split("\t")
        en, xx = (en.strip(), xx.strip())
        keep.append((en, xx))
            
    random.shuffle(keep)
    sample = keep[:GLEU_EVALUATION_SAMPLE_SIZE]
    return sample

def inference(
    input_text: str,
    req_session: requests.Session,
    priority: InferencePriorityType = InferencePriorityType.accuracy,
    detail: InferenceDetailType = InferenceDetailType.predict_next    
) -> str:
    """Makes an inference with the model"""
    endpoint = (
        f"{API_URL}"
        f"/showcase/{SESSION_KEY}"
        f"/inference/{priority.value}"
        f"/{REVISION_NUMBER}"
        f"/{detail.value}"
    )
    
    try:
        response = req_session.post(endpoint, data=json.dumps(input_text), headers=HEADERS)

        if response.status_code == 200:
            return response.json()
        else:
            raise Exception(f"Error calling inference: {response.json()}")
    except:
        raise Exception(f"Error calling inference, check network connection and try again")

def evaluate_translation_model(iter):
    start = time.monotonic()
    
    req_session = requests.Session()

    sample = sample_translation_set(
        path=Path(f"{TEST_PATH}/").resolve())

    data = [
        (
            *s,
            p := inference(
                s[0],
                req_session,
                InferencePriorityType.index,
                InferenceDetailType.translate_line                
            ),
            p['content'] == s[1],
            sentence_gleu([s[1]], p['content']),
        )
        for s in sample
    ]        

    gleu_avg = round(sum(map(lambda x: x[4], data)) / len(sample), 2)

    end = time.monotonic()
    
    elapsed = round(end - start, 2)

    results = (
        f"Iteration:   ({iter})\n"
        f"Sample size: {len(sample)}\n"
        f"GLEU:        {gleu_avg}\n"
        f"Time:        {elapsed}s"
    )

    print(results)

    header = "Source\tTarget\tTranslation\tGLEU"
    
    lines = [
        results,
        "\n===\n",
        header,
        *["\t".join(map(str, d)) for d in data],
    ]
    
    results_file = Path(f"{SESSION_KEY}_TRANSLATION_RESULTS_{iter}.txt")
    
    results_file.write_text("\n".join(lines), encoding="utf-8")

    print(f"Results written to {str(results_file.absolute())}")        

if __name__ == "__main__":    
    iterations = list(range(1, GLEU_ITERATION_COUNT + 1))

    for i in iterations:
        evaluate_translation_model(i)