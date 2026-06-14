"""Pytest port of repos/ulf-lib/test/ttt-phrasal-patterns.lisp."""
import pytest

from ulf_py.phrasal import (
    phrasal_ulf_type,
    noun_p, adj_p, verb_p, tensed_verb_p, term_p,
    sent_p, tensed_sent_p, sent_mod_p, pred_p,
    aux_p, tensed_aux_p, pp_p, ps_p, p_arg_p,
    plur_lex_noun_p, pasv_lex_verb_p, perf_lex_verb_p, prog_lex_verb_p,
    tensed_lex_verbaux_p, plur_noun_p, plur_partitive_p, plur_term_p,
)
from ulf_py.lexical import lex_verb_p, lex_noun_p, lex_tense_p, lex_p_p


# ---------------------------------------------------------------------------
# ttt-p-arg-mod (direct port of define-test ttt-p-arg-mod)
# ---------------------------------------------------------------------------

def test_mod_a_applied_to_ps_is_sent_mod() -> None:
    """(right.mod-a (before.ps ...)) should be classified as sent-mod."""
    expr = ('right.mod-a', ('before.ps', ('i.pro', (('past', 'move.v'), 'it.pro'))))
    assert phrasal_ulf_type(expr) == ['sent-mod']


def test_mod_n_applied_to_ps_is_unknown() -> None:
    """(right.mod-n (before.ps ...)) has no recognized type."""
    expr = ('right.mod-n', ('before.ps', ('i.pro', (('past', 'move.v'), 'it.pro'))))
    assert phrasal_ulf_type(expr) == ['unknown']


# ---------------------------------------------------------------------------
# Basic phrasal predicates (smoke tests, not in Lisp test suite)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("atom", ["man.n", "dog.n", "woman.n"])
def test_lex_nouns_are_nouns(atom: str) -> None:
    assert noun_p(atom)


@pytest.mark.parametrize("atom", ["run.v", "eat.v", "sleep.v"])
def test_lex_verbs_are_verbs(atom: str) -> None:
    assert verb_p(atom)


@pytest.mark.parametrize("atom", ["big.a", "red.a", "happy.a"])
def test_lex_adjs_are_adjs(atom: str) -> None:
    assert adj_p(atom)


@pytest.mark.parametrize("atom", ["he.pro", "she.pro", "it.pro", "|John|"])
def test_pronouns_and_names_are_terms(atom: str) -> None:
    assert term_p(atom)


def test_tensed_verb_form() -> None:
    assert tensed_verb_p(('past', 'run.v'))


def test_verb_with_object() -> None:
    assert verb_p(('eat.v', 'it.pro'))


def test_subject_verb_is_sent() -> None:
    assert sent_p(('he.pro', 'run.v'))


def test_subject_tensed_verb_is_tensed_sent() -> None:
    assert tensed_sent_p(('he.pro', ('past', 'run.v')))


# ---------------------------------------------------------------------------
# gen-phrasal predicates
# ---------------------------------------------------------------------------

def test_plur_lex_noun_p_basic() -> None:
    assert plur_lex_noun_p(('plur', 'man.n'))
    assert plur_lex_noun_p(('plur', 'dog.n'))
    assert not plur_lex_noun_p(('plur', 'run.v'))
    assert not plur_lex_noun_p('man.n')


def test_pasv_lex_verb_p_basic() -> None:
    assert pasv_lex_verb_p(('pasv', 'run.v'))
    assert pasv_lex_verb_p(('pasv', 'eat.v'))
    assert not pasv_lex_verb_p(('pasv', 'man.n'))
    assert not pasv_lex_verb_p('run.v')


def test_perf_lex_verb_p_basic() -> None:
    assert perf_lex_verb_p(('perf', 'run.v'))
    assert not perf_lex_verb_p(('perf', 'man.n'))


def test_prog_lex_verb_p_basic() -> None:
    assert prog_lex_verb_p(('prog', 'run.v'))
    assert not prog_lex_verb_p(('prog', 'man.n'))


def test_tensed_lex_verbaux_p_basic() -> None:
    assert tensed_lex_verbaux_p(('past', 'run.v'))
    assert tensed_lex_verbaux_p(('pres', 'eat.v'))
    assert not tensed_lex_verbaux_p(('past', 'man.n'))
    assert not tensed_lex_verbaux_p('run.v')


def test_plur_noun_p_plur_form() -> None:
    assert plur_noun_p(('plur', 'man.n'))
    assert plur_noun_p(('plur', 'dog.n'))
    assert not plur_noun_p(('plur', 'run.v'))


def test_plur_term_p_plural_pronouns() -> None:
    for pro in ('they.pro', 'them.pro', 'we.pro', 'us.pro', 'those.pro', 'these.pro'):
        assert plur_term_p(pro), f"{pro} should be plural"


def test_plur_term_p_singular_pronoun_is_not_plural() -> None:
    assert not plur_term_p('he.pro')
    assert not plur_term_p('she.pro')
    assert not plur_term_p('it.pro')


def test_plur_term_p_plural_det_np() -> None:
    assert plur_term_p(('these.d', 'man.n'))
    assert plur_term_p(('those.d', 'dog.n'))
    assert plur_term_p(('many.d', 'cat.n'))


def test_plur_term_p_plur_noun_np() -> None:
    assert plur_term_p(('the.d', ('plur', 'man.n')))
