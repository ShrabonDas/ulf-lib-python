"""Pytest port of repos/ulf-lib/test/syntactic-features.lisp.

Covers synfeat propagation rules through compose-types.
"""
import pytest

import ulf_py.semtype as semtype_module
from ulf_py.semtype import str2semtype, semtype2str
from ulf_py.composition import apply_operator


def _str2str_compose(opr_str: str, arg_str: str) -> str | None:
    """Compose two semtype strings using right-apply (mirrors Lisp compose-types!)."""
    result = apply_operator(
        str2semtype(opr_str, extended=True),
        str2semtype(arg_str, extended=True),
        ignore_synfeats=False,
    )
    return semtype2str(result) if result is not None else None


def _equal_str(left: str, right: str) -> bool:
    """True if two semtype strings parse to equal semtypes."""
    return semtype_module.semtype_equal(
        str2semtype(left, extended=True),
        str2semtype(right, extended=True),
    )


# ---------------------------------------------------------------------------
# basic-synfeats-composition
# ---------------------------------------------------------------------------
# Tense propagates to predicates AND sentences.
# Plurality (PL) and Passive (PV) only propagate to predicates (dropped at sentences).
# Auxiliary (X), Perfect (PF), Progressive (PG) propagate to sentences.

class TestBasicSynfeatsComposition:
    """Port of define-test basic-synfeats-composition."""

    def test_tense_propagates_to_sentence(self) -> None:
        """compose((D=>(S=>2))%T, D) → (S=>2)%T."""
        result = _str2str_compose("(D=>(S=>2))%T", "D")
        assert result is not None
        assert _equal_str("(S=>2)%T", result)

    def test_tense_drops_on_non_pred_range(self) -> None:
        """compose((D=>2)%T, D) → 2 (no tense on propositional 2)."""
        result = _str2str_compose("(D=>2)%T", "D")
        assert result is not None
        assert _equal_str("2", result)

    def test_tense_partial_application(self) -> None:
        """compose((D=>(D=>2))%T, D) → (D=>2) with no tense (non-pred range)."""
        result = _str2str_compose("(D=>(D=>2))%T", "D")
        assert result is not None
        assert _equal_str("(D=>2)", result)

    @pytest.mark.parametrize("feat", ["X", "PL", "PF", "PV", "PG"])
    def test_feature_propagates_through_partial_application(self, feat: str) -> None:
        """compose((D=>(D=>(S=>2)))%feat, D) → (D=>(S=>2))%feat."""
        result = _str2str_compose(f"(D=>(D=>(S=>2)))%{feat}", "D")
        assert result is not None, f"compose((D=>(D=>(S=>2)))%{feat}, D) should not be None"
        assert _equal_str(f"(D=>(S=>2))%{feat}", result), (
            f"Expected (D=>(S=>2))%{feat}, got {result}"
        )

    @pytest.mark.parametrize("feat", ["PL", "PV"])
    def test_pred_only_feat_drops_at_sentence(self, feat: str) -> None:
        """compose((D=>(S=>2))%{PL,PV}, D) → (S=>2) (feat dropped at sentence boundary)."""
        result = _str2str_compose(f"(D=>(S=>2))%{feat}", "D")
        assert result is not None, f"compose((D=>(S=>2))%{feat}, D) should not be None"
        assert _equal_str("(S=>2)", result), (
            f"Expected bare (S=>2) for {feat} propagation, got {result}"
        )

    @pytest.mark.parametrize("feat", ["X", "PF", "PG"])
    def test_sent_feat_propagates_to_sentence(self, feat: str) -> None:
        """compose((D=>(S=>2))%{X,PF,PG}, D) → (S=>2)%feat."""
        result = _str2str_compose(f"(D=>(S=>2))%{feat}", "D")
        assert result is not None, f"compose((D=>(S=>2))%{feat}, D) should not be None"
        assert _equal_str(f"(S=>2)%{feat}", result), (
            f"Expected (S=>2)%{feat}, got {result}"
        )


# ---------------------------------------------------------------------------
# multiple-synfeats-composition
# ---------------------------------------------------------------------------

class TestMultipleSynfeatsComposition:
    """Port of define-test multiple-synfeats-composition."""

    @pytest.mark.parametrize("feat1,feat2", [
        (f1, f2)
        for f1 in ["X", "PL", "PF", "PV", "PG"]
        for f2 in ["X", "PL", "PF", "PV", "PG"]
        if f1 != f2
    ])
    def test_partial_application_preserves_both_feats(self, feat1: str, feat2: str) -> None:
        """compose((D=>(D=>(S=>2)))%feat1,feat2, D) → (D=>(S=>2))%feat1,feat2."""
        result = _str2str_compose(f"(D=>(D=>(S=>2)))%{feat1},{feat2}", "D")
        assert result is not None
        assert _equal_str(f"(D=>(S=>2))%{feat1},{feat2}", result), (
            f"Expected (D=>(S=>2))%{feat1},{feat2}, got {result}"
        )

    @pytest.mark.parametrize("feat1,feat2", [
        (f1, f2)
        for f1 in ["PL", "PV"]
        for f2 in ["PL", "PV"]
        if f1 != f2
    ])
    def test_both_pred_only_feats_drop_at_sentence(self, feat1: str, feat2: str) -> None:
        """Both PL/PV → (S=>2) with no features."""
        result = _str2str_compose(f"(D=>(S=>2))%{feat1},{feat2}", "D")
        assert result is not None
        assert _equal_str("(S=>2)", result), (
            f"Expected bare (S=>2) for {feat1},{feat2}, got {result}"
        )

    @pytest.mark.parametrize("feat1,feat2", [
        (f1, f2)
        for f1 in ["X", "PF", "PG"]
        for f2 in ["X", "PF", "PG"]
        if f1 != f2
    ])
    def test_both_sent_feats_propagate(self, feat1: str, feat2: str) -> None:
        """Both X/PF/PG → (S=>2)%feat1,feat2."""
        result = _str2str_compose(f"(D=>(S=>2))%{feat1},{feat2}", "D")
        assert result is not None
        assert _equal_str(f"(S=>2)%{feat1},{feat2}", result), (
            f"Expected (S=>2)%{feat1},{feat2}, got {result}"
        )

    @pytest.mark.parametrize("pred_only,sent_feat", [
        (p, s)
        for p in ["PL", "PV"]
        for s in ["X", "PF", "PG"]
    ])
    def test_mixed_feats_sent_feat_survives(self, pred_only: str, sent_feat: str) -> None:
        """One pred-only + one sent-feat → only the sent-feat survives."""
        result = _str2str_compose(f"(D=>(S=>2))%{pred_only},{sent_feat}", "D")
        assert result is not None
        assert _equal_str(f"(S=>2)%{sent_feat}", result), (
            f"Expected (S=>2)%{sent_feat}, got {result}"
        )

    @pytest.mark.parametrize("sent_feat,pred_only", [
        (s, p)
        for s in ["X", "PF", "PG"]
        for p in ["PL", "PV"]
    ])
    def test_mixed_feats_reversed_order(self, sent_feat: str, pred_only: str) -> None:
        """Order of feats in string shouldn't matter; same rule applies."""
        result = _str2str_compose(f"(D=>(S=>2))%{sent_feat},{pred_only}", "D")
        assert result is not None
        assert _equal_str(f"(S=>2)%{sent_feat}", result), (
            f"Expected (S=>2)%{sent_feat}, got {result}"
        )
