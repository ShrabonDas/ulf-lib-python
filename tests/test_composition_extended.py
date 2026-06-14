"""Port of repos/ulf-lib/test/composition.lisp.

Covers basic_compose, basic_macro_compose, qt_attr_compose, aux_compose,
p_arg_compose, sentential_punctuation_compose, comp_p_arg_mod, subject_vp,
free_sent_mod, itaux, ulf_type_string_basic, ulf_type_string_named_predicates,
and aspect_pasv.
"""
import pytest
from ulf_py.semtype import str2semtype, semtype2str, semtype_match
from ulf_py.composition import (
    compose_types,
    extended_compose_types,
    left_right_compose_types,
)
from ulf_py.type_inference import ulf_type, ulf_type_string


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sm(s1: str | None, s2: str | None) -> bool:
    """semtype_match with extended string inputs; pattern first."""
    if s1 is None or s2 is None:
        return False
    return semtype_match(str2semtype(s1, extended=True), str2semtype(s2, extended=True))


def _ses(s1: str | None, s2: str | None) -> bool:
    """Bidirectional semtype_match between two semtype strings."""
    if s1 is None and s2 is None:
        return True
    if s1 is None or s2 is None:
        return False
    t1 = str2semtype(s1, extended=True)
    t2 = str2semtype(s2, extended=True)
    return semtype_match(t1, t2) or semtype_match(t2, t1)


def _cstr(ulf1, ulf2, ext: str = "basic") -> str | None:
    """Compose the types of ulf1 and ulf2 and return the semtype string."""
    t1 = ulf_type(ulf1)
    t2 = ulf_type(ulf2)
    if ext == "basic":
        result = compose_types(t1, t2).semtype
    elif ext == "extended":
        result = extended_compose_types(t1, t2).semtype
    elif ext == "left-right":
        result = left_right_compose_types(t1, t2).semtype
    else:
        raise ValueError(f"Unknown composition variant: {ext!r}")
    return semtype2str(result)


def _cres(ulf1, ulf2, ext: str = "basic"):
    """Compose the types of ulf1 and ulf2 and return the CompositionResult."""
    t1 = ulf_type(ulf1)
    t2 = ulf_type(ulf2)
    if ext == "basic":
        return compose_types(t1, t2)
    elif ext == "extended":
        return extended_compose_types(t1, t2)
    elif ext == "left-right":
        return left_right_compose_types(t1, t2)
    raise ValueError(f"Unknown composition variant: {ext!r}")


# ---------------------------------------------------------------------------
# basic_compose
# ---------------------------------------------------------------------------

class TestBasicCompose:
    def test_det_noun(self):
        assert _cstr("the.d", "man.n") == "D"

    def test_det_det_none(self):
        assert _cstr("the.d", "the.d") is None

    def test_transitive_verb_applied(self):
        # (help.v me.pro) should be a verb semtype
        result_str = semtype2str(ulf_type(("help.v", "me.pro")))
        pattern = (
            "{(S=>2)_V|{(D=>(S=>2))_V|{({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}=>(D=>(S=>2)))_V"
            "|{({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}^2=>(D=>(S=>2)))_V"
            "|{({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}^3=>(D=>(S=>2)))_V"
            "|({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}^4=>(D=>(S=>2)))_V}}}}}"
        )
        assert _sm(result_str, pattern)

    def test_be_pronoun_none(self):
        assert _cstr("be.v", "me.pro") is None

    def test_be_adjective(self):
        result_str = semtype2str(ulf_type(("be.v", "happy.a")))
        assert _sm(result_str, "(D=>(S=>2))_V")


# ---------------------------------------------------------------------------
# basic_macro_compose
# ---------------------------------------------------------------------------

class TestBasicMacroCompose:
    def test_tense_verb(self):
        result = ulf_type_string(("pres", "run.v"))
        expected = (
            "{(D=>(S=>2))_V%T|{{(D=>(D=>(S=>2)))_V%T"
            "|((D=>(S=>2))%!T,!PF,!PG,!PV,!X=>(D=>(S=>2)))_V%T}"
            "|{({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}^2=>(D=>(S=>2)))_V%T"
            "|{({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}^3=>(D=>(S=>2)))_V%T"
            "|{({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}^4=>(D=>(S=>2)))_V%T"
            "|({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}^5=>(D=>(S=>2)))_V%T}}}}}"
        )
        assert _sm(result, expected)

    def test_tense_adjective_none(self):
        assert _cstr("past", "happy.a", "extended") is None

    def test_tense_noun_none(self):
        assert _cstr("cf", "man.n", "extended") is None

    def test_n_plus_preds_noun(self):
        result_str = semtype2str(ulf_type(("n+preds", "man.n")))
        assert _sm(result_str, "{+PREDS[N+[(D=>(S=>2))_N%LEX]]|(D=>(S=>2))_N%LEX}")

    def test_np_plus_preds_pronoun(self):
        assert _cstr("np+preds", "he.pro", "extended") == "{+PREDS[NP+[D]]|D}"

    def test_sub_pronoun(self):
        assert _cstr("sub", "he.pro", "extended") == "SUB1[D]"

    def test_rep_noun_none(self):
        assert _cstr("rep", "man.n", "extended") is None

    def test_det_hole(self):
        result = _cstr("the.d", "*p", "extended")
        assert _ses(result, "D[*P[{(D=>(S=>2))_N|(D=>(S=>2))_P}]]")

    def test_rep_det_hole(self):
        result = _cstr("rep", ("the.d", "*p"), "extended")
        assert _ses(result, "REP1[D[*P[{(D=>(S=>2))_N|(D=>(S=>2))_P}]]]")

    def test_qt_attr_pronoun_none(self):
        assert _cstr("qt-attr", "her.pro", "extended") is None

    def test_verb_qt_hole(self):
        result_str = ulf_type_string(("say.v", "*qt"))
        expected = (
            "{(S=>2)_V[*QT]|{(D=>(S=>2))_V[*QT]"
            "|{({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}=>(D=>(S=>2)))_V[*QT]"
            "|{({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}^2=>(D=>(S=>2)))_V[*QT]"
            "|{({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}^3=>(D=>(S=>2)))_V[*QT]"
            "|({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}^4=>(D=>(S=>2)))_V[*QT]}}}}}"
        )
        assert _sm(result_str, expected)

    def test_qt_attr_verb_qt_hole(self):
        result_str = ulf_type_string(("qt-attr", ("say.v", "*qt")))
        expected = (
            "QT-ATTR1[{(S=>2)_V[*QT]|{(D=>(S=>2))_V[*QT]|{(D=>(D=>(S=>2)))_V[*QT]"
            "|{((D=>(S=>2))%!T,!PF,!PG,!PV,!X=>(D=>(S=>2)))_V[*QT]"
            "|{({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}^2=>(D=>(S=>2)))_V[*QT]"
            "|{({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}^3=>(D=>(S=>2)))_V[*QT]"
            "|({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}^4=>(D=>(S=>2)))_V[*QT]}}}}}}]"
        )
        assert _sm(result_str, expected)

    def test_postgen_name(self):
        result = _cstr("|Gene|", "|'S|", "extended")
        assert _ses(result, "POSTGEN2")

    def test_postgen_det(self):
        result = _cstr(("|Gene|", "|'S|"), "dog.n", "extended")
        assert _ses(result, "D")


# ---------------------------------------------------------------------------
# qt_attr_compose
# ---------------------------------------------------------------------------

class TestQtAttrCompose:
    def test_quote_type(self):
        assert ulf_type_string('"') == '"'

    def test_qt_hole_type(self):
        assert ulf_type_string("*qt") == "D[*QT]"

    def test_eq_qt(self):
        assert _cstr("=", "*qt", "extended") == "{(D=>(S=>2))_A[*QT]|(D=>(S=>2))_P[*QT]}"

    def test_qt_attr_eq_qt(self):
        assert _cstr("qt-attr", ("=", "*qt"), "extended") == (
            "QT-ATTR1[{(D=>(S=>2))_A[*QT]|(D=>(S=>2))_P[*QT]}]"
        )

    def test_qt_attr_applied_pronoun(self):
        assert _cstr(("qt-attr", ("=", "*qt")), "it.pro", "extended") == (
            "D[QT-ATTR1[{(D=>(S=>2))_A[*QT]|(D=>(S=>2))_P[*QT]}]]"
        )

    def test_quote_qt_attr(self):
        assert _cstr('"', (("qt-attr", ("=", "*qt")), "it.pro"), "extended") == (
            "QT-ATTR2[{(D=>(S=>2))_A[*QT]|(D=>(S=>2))_P[*QT]}]"
        )

    def test_closing_quote(self):
        assert _cstr(('"', (("qt-attr", ("=", "*qt")), "it.pro")), '"', "extended") == (
            "{(D=>(S=>2))_A|(D=>(S=>2))_P}"
        )


# ---------------------------------------------------------------------------
# aux_compose
# ---------------------------------------------------------------------------

class TestAuxCompose:
    def test_aux_verb(self):
        result = _cstr("do.aux-s", "run.v", "extended")
        assert _sm(result, "(D=>(S=>2))_V%X,!T")

    def test_tense_aux(self):
        result = _cstr("past", "do.aux-s", "extended")
        assert _sm(result, "((D=>(S=>2))_V%!T,!X>>(D=>(S=>2))_V%T,X)")

    def test_tensed_aux_verb(self):
        result = _cstr(("past", "do.aux-s"), "run.v", "extended")
        assert _sm(result, "(D=>(S=>2))_V%X,T")

    def test_double_aux_none(self):
        assert _cstr("do.aux-s", ("do.aux-s", "run.v"), "extended") is None

    def test_double_tense_none(self):
        assert _cstr("past", ("past", "do.aux-s"), "extended") is None

    def test_tensed_aux_double_none(self):
        assert _cstr(("past", "do.aux-s"), ("do.aux-s", "run.v"), "extended") is None


# ---------------------------------------------------------------------------
# p_arg_compose
# ---------------------------------------------------------------------------

class TestPArgCompose:
    def test_p_arg_type(self):
        assert ulf_type_string("with.p-arg") == "PARG"

    def test_p_arg_term(self):
        result = _cstr("in.p-arg", "that.pro", "extended")
        assert _sm(result, "PARG1[D]")

    def test_p_arg_noun(self):
        result = _cstr("as.p-arg", "chicken.n", "extended")
        assert _sm(result, "PARG1[(D=>(S=>2))_N%!LEX]")

    def test_verb_p_arg(self):
        result = _cstr("sleep.v", ("in.p-arg", "that.pro"), "extended")
        expected = (
            "{(S=>2)_V|{(D=>(S=>2))_V"
            "|{({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}=>(D=>(S=>2)))_V"
            "|{({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}^2=>(D=>(S=>2)))_V"
            "|{({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}^3=>(D=>(S=>2)))_V"
            "|({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}^4=>(D=>(S=>2)))_V}}}}}"
        )
        assert _sm(result, expected)

    def test_verb_noun_p_arg(self):
        result = _cstr("dress.v", ("as.p-arg", "chicken.n"), "extended")
        expected = (
            "{(D=>(S=>2))_V"
            "|{({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}=>(D=>(S=>2)))_V"
            "|{({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}^2=>(D=>(S=>2)))_V"
            "|{({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}^3=>(D=>(S=>2)))_V"
            "|({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}^4=>(D=>(S=>2)))_V}}}}"
        )
        assert _sm(result, expected)

    def test_adj_p_arg(self):
        result = _cstr("liked.a", ("by.p-arg", ("the.d", "audience.n")), "extended")
        assert _sm(result, "{(D=>(S=>2))_A%!LEX|(D=>(D=>(S=>2)))_A%!LEX}")

    def test_noun_p_arg(self):
        result = _cstr("sale.n", ("of.p-arg", ("his.d", "car.n")), "extended")
        assert _sm(result, "(D=>(S=>2))_N%!LEX")

    def test_prep_p_arg_none(self):
        assert _cstr("in.p", ("in.p-arg", "that.pro")) is None

    def test_det_p_arg_none(self):
        assert _cstr("the.d", ("of.p-arg", ("k", "force.n"))) is None

    def test_pronoun_p_arg_none(self):
        assert _cstr("him.pro", ("in.p-arg", "that.pro")) is None

    def test_adv_p_arg_none(self):
        assert _cstr("quickly.adv-a", ("at.p-arg", "her.pro")) is None


# ---------------------------------------------------------------------------
# sentential_punctuation_compose
# ---------------------------------------------------------------------------

class TestSententialPunctuationCompose:
    def test_exclamation_type(self):
        assert ulf_type_string("!") == "((S=>2)_V>>(S=>2))%LEX"

    def test_question_type(self):
        assert ulf_type_string("?") == "((S=>2)_V>>(S=>2))%LEX"

    def test_sentence_exclamation(self):
        result = _cstr(("i.pro", ("go.v", "there.pro")), "!", "extended")
        assert _sm(result, "(S=>2)_v")

    def test_sentence_question(self):
        result = _cstr(("i.pro", ("go.v", "there.pro")), "?", "extended")
        assert _sm(result, "(S=>2)_v")

    def test_exclamation_tensed_sentence(self):
        result = _cstr("!", ("i.pro", (("past", "go.v"), "there.pro")), "extended")
        assert _sm(result, "(S=>2)_v%T")

    def test_question_tensed_sentence(self):
        result = _cstr("?", ("i.pro", (("past", "go.v"), "there.pro")), "extended")
        assert _sm(result, "(S=>2)_v%T")


# ---------------------------------------------------------------------------
# comp_p_arg_mod
# ---------------------------------------------------------------------------

_BEFORE_PS_ULF = ("before.ps", ("i.pro", (("past", "move.v"), "it.pro")))


class TestCompPArgMod:
    def test_mod_a_ps(self):
        result = _cstr("right.mod-a", _BEFORE_PS_ULF)
        assert _ses(result, "((S=>2)_v>>(S=>2))_p")

    def test_mod_a_complex_ps(self):
        result = _cstr(("mod-a", "right.a"), _BEFORE_PS_ULF)
        assert _ses(result, "((S=>2)_v>>(S=>2))_p")

    def test_mod_n_ps_none(self):
        assert _cstr("right.mod-n", _BEFORE_PS_ULF) is None


# ---------------------------------------------------------------------------
# subject_vp
# ---------------------------------------------------------------------------

class TestSubjectVP:
    def test_subject_verb_left_right_direction(self):
        res = _cres("he.pro", "run.v", "left-right")
        assert res.direction == "right"

    def test_subject_verb_left_right_type(self):
        res = _cres("he.pro", "run.v", "left-right")
        big_opt = (
            "{(S=>2)_V|{(D=>(S=>2))_V"
            "|{({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}=>(D=>(S=>2)))_V"
            "|{({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}^2=>(D=>(S=>2)))_V"
            "|{({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}^3=>(D=>(S=>2)))_V"
            "|({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}^4=>(D=>(S=>2)))_V}}}}}"
        )
        assert _sm(semtype2str(res.semtype), big_opt)

    def test_subject_verb_extended_direction(self):
        res = _cres("he.pro", "run.v", "extended")
        assert res.direction == "left"

    def test_subject_verb_extended_type(self):
        res = _cres("he.pro", "run.v", "extended")
        big_opt = (
            "{(S=>2)_V|{(D=>(S=>2))_V"
            "|{({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}=>(D=>(S=>2)))_V"
            "|{({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}^2=>(D=>(S=>2)))_V"
            "|{({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}^3=>(D=>(S=>2)))_V"
            "|({D|(D=>(S=>2))%!T,!PF,!PG,!PV,!X}^4=>(D=>(S=>2)))_V}}}}}"
        )
        assert _sm(semtype2str(res.semtype), big_opt)

    def test_subject_tensed_aux_verb_left_right_direction(self):
        res = _cres("it.pro", (("pres", "do.aux-s"), "see.v"), "left-right")
        assert res.direction == "right"

    def test_subject_tensed_aux_verb_left_right_type(self):
        res = _cres("it.pro", (("pres", "do.aux-s"), "see.v"), "left-right")
        assert _sm(semtype2str(res.semtype), "(S=>2)_V%T,X")

    def test_subject_tensed_aux_verb_extended_direction(self):
        res = _cres("it.pro", (("pres", "do.aux-s"), "see.v"), "extended")
        assert res.direction == "left"

    def test_subject_tensed_aux_verb_extended_type(self):
        res = _cres("it.pro", (("pres", "do.aux-s"), "see.v"), "extended")
        assert _sm(semtype2str(res.semtype), "(S=>2)_V%T,X")


# ---------------------------------------------------------------------------
# free_sent_mod
# ---------------------------------------------------------------------------

_SENT_MODS = [
    "not",
    "not.adv-s",
    "always.adv-f",
    "today.adv-e",
    ("when.ps", ("i.pro", ("past", "sleep.v"))),
]

_ULF_SEGMENTS = [
    "he.pro",
    "run.v",
    "dog.n",
    ("past", "run.v"),
    ("past", "do.aux-s"),
    ("k", "dog.n"),
    (("past", "see.v"), "him.pro"),
    ("i.pro", (("past", "see.v"), "him.pro")),
]


class TestFreeSentMod:
    def test_not_type(self):
        assert _ses(ulf_type_string("not"), "((S=>2)_v>>(S=>2))%lex")

    def test_not_adv_s_type(self):
        assert _ses(ulf_type_string("not.adv-s"), "((S=>2)_v>>(S=>2))%lex")

    def test_always_adv_f_type(self):
        assert _ses(ulf_type_string("always.adv-f"), "((S=>2)_v>>(S=>2))%lex")

    def test_today_adv_e_type(self):
        assert _ses(ulf_type_string("today.adv-e"), "((S=>2)_v>>(S=>2))%lex")

    def test_when_ps_type(self):
        result = ulf_type_string(("when.ps", ("i.pro", ("past", "sleep.v"))))
        assert _sm(result, "((S=>2)_v>>(S=>2))")

    @pytest.mark.parametrize("seg", _ULF_SEGMENTS)
    @pytest.mark.parametrize("mod", _SENT_MODS)
    def test_mod_seg_passthrough(self, mod, seg):
        seg_str = ulf_type_string(seg)
        res = _cres(mod, seg, "left-right")
        assert res.direction == "right", f"mod+seg direction wrong: {mod!r}, {seg!r}"
        assert _ses(semtype2str(res.semtype), seg_str), (
            f"mod+seg type wrong: {mod!r}, {seg!r} → {semtype2str(res.semtype)!r}"
        )

    @pytest.mark.parametrize("seg", _ULF_SEGMENTS)
    @pytest.mark.parametrize("mod", _SENT_MODS)
    def test_seg_mod_passthrough(self, mod, seg):
        seg_str = ulf_type_string(seg)
        res = _cres(seg, mod, "left-right")
        assert res.direction == "right", f"seg+mod direction wrong: {seg!r}, {mod!r}"
        assert _ses(semtype2str(res.semtype), seg_str), (
            f"seg+mod type wrong: {seg!r}, {mod!r} → {semtype2str(res.semtype)!r}"
        )


# ---------------------------------------------------------------------------
# itaux
# ---------------------------------------------------------------------------

class TestItAux:
    def test_inverted_aux_pronoun(self):
        result = _cstr(("past", "do.aux-s"), "him.pro")
        assert _sm(result, "((D=>(S=>2))_V%!T,!X>>(S=>2)_v%T,X)")

    def test_inverted_aux_subject_verb(self):
        result = _cstr((("past", "do.aux-s"), "he.pro"), "run.v")
        assert _sm(result, "(S=>2)_v%T,X")

    def test_inverted_aux_noun_none(self):
        assert _cstr(("past", "do.aux-s"), "dog.n", "left-right") is None

    def test_inverted_aux_tensed_verb_none(self):
        assert _cstr((("past", "do.aux-s"), "he.pro"), ("pres", "run.v")) is None

    def test_inverted_aux_pronoun_none(self):
        assert _cstr((("past", "do.aux-s"), "he.pro"), "him.pro") is None

    def test_inverted_aux_double_aux_none(self):
        assert _cstr(
            (("past", "do.aux-s"), "he.pro"), (("pres", "may.aux-s"), "see.v")
        ) is None


# ---------------------------------------------------------------------------
# ulf_type_string_basic
# ---------------------------------------------------------------------------

class TestUlfTypeStringBasic:
    def test_det_n_plus_preds(self):
        assert ulf_type_string(
            ("the.d", ("n+preds", "man.n", ("under.p", ("the.d", "bridge.n"))))
        ) == "D"

    def test_det_mod_n_noun(self):
        assert ulf_type_string(("the.d", (("mod-n", "big.a"), "man.n"))) == "D"

    def test_det_mod_n_noun_alt(self):
        assert ulf_type_string(("a.d", (("mod-n", "melting.n"), "pot.n"))) == "D"

    def test_that_sentence(self):
        assert ulf_type_string(("that", ("|Mary|", ("past", "run.v")))) == "D"

    def test_np_plus_preds(self):
        assert ulf_type_string(
            ("np+preds", "|John|", ("on.p", ("the.d", "bridge.n")))
        ) == "{+PREDS[NP+[D]]|D}"

    def test_det_adj_noun_none(self):
        assert ulf_type_string(("the.d", ("big.a", "man.n"))) is None

    def test_det_noun_noun_none(self):
        assert ulf_type_string(("a.d", ("melting.n", "pot.n"))) is None

    def test_det_type(self):
        # Lisp distributes: {((D=>(S=>2))_N=>D)%LEX|((D=>(S=>2))_P=>D)%LEX}
        # Python is undistributed but semtype_match confirms equivalence.
        result = ulf_type_string("a.d")
        assert _ses(result, "{((D=>(S=>2))_N=>D)%LEX|((D=>(S=>2))_P=>D)%LEX}")


# ---------------------------------------------------------------------------
# ulf_type_string_named_predicates
# ---------------------------------------------------------------------------

class TestUlfTypeStringNamedPredicates:
    def test_number_adj(self):
        result = ulf_type_string("19.a")
        assert _sm(result, "{(D=>(S=>2))_A%LEX|(D=>(D=>(S=>2)))_A%LEX}")

    def test_name_noun(self):
        result = ulf_type_string("|Man|.n")
        assert _sm(result, "(D=>(S=>2))_N%LEX")


# ---------------------------------------------------------------------------
# aspect_pasv
# ---------------------------------------------------------------------------

class TestAspectPasv:
    def test_pasv_verb(self):
        result = semtype2str(ulf_type(("pasv", "run.v")))
        assert _sm(result, "(D=>(S=>2))_V%LEX,!T,PV")

    def test_pres_pasv_verb(self):
        result = semtype2str(ulf_type(("pres", ("pasv", "run.v"))))
        assert _sm(result, "(D=>(S=>2))_V%LEX,T,PV")

    def test_perf_pasv_verb(self):
        result = semtype2str(ulf_type(("perf", ("pasv", "run.v"))))
        assert _sm(result, "(D=>(S=>2))_V%!LEX,!T,PF,PV")

    def test_pres_perf_pasv_verb(self):
        result = semtype2str(ulf_type((("pres", "perf"), ("pasv", "run.v"))))
        assert _sm(result, "(D=>(S=>2))_V%!LEX,T,PF,PV")
