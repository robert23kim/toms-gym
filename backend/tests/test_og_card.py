"""DB-free unit tests for OG share-card generation + meta rendering (T13).

Runs under run_ci_tests.sh with --noconftest: no live DB, no GCS. Only the pure
renderers (og_card) and the pure crawler-detection helper are exercised here;
the DB/GCS-touching /s/<code> route path is covered separately with a database.
"""

from toms_gym.integrations import og_card
from toms_gym.routes.short_link_routes import _is_crawler


# --- card image ------------------------------------------------------------

def test_render_card_png_is_valid_png():
    png = og_card.render_card_png("lift", "Tom's Squat", "A", "3 reps · 225 lbs")
    assert isinstance(png, (bytes, bytearray))
    assert png[:8] == b"\x89PNG\r\n\x1a\n"  # PNG magic
    assert len(png) > 1000  # non-trivial image


def test_render_card_png_all_kinds():
    for kind in ("lift", "bowling", "golf", "default", "nonsense"):
        png = og_card.render_card_png(kind, "Title", "42", "desc")
        assert png[:8] == b"\x89PNG\r\n\x1a\n"


def test_render_card_png_handles_empty_and_long():
    # No stat, no description, and an overlong stat that must shrink to fit.
    png = og_card.render_card_png("golf", "A Very Long Golf Course Name That Wraps", "", "")
    assert png[:8] == b"\x89PNG\r\n\x1a\n"
    png2 = og_card.render_card_png("bowling", "x", "Straightaway", "")
    assert png2[:8] == b"\x89PNG\r\n\x1a\n"


# --- kind inference --------------------------------------------------------

def test_infer_kind():
    assert og_card.infer_kind("https://f/bowling/result/1") == "bowling"
    assert og_card.infer_kind("https://f/golf/round/1") == "golf"
    assert og_card.infer_kind("https://f/challenges/c/participants/p/video/v") == "lift"
    assert og_card.infer_kind("https://f/something/else") == "default"
    assert og_card.infer_kind("") == "default"


# --- meta HTML -------------------------------------------------------------

def test_render_meta_html_has_og_tags():
    html_doc = og_card.render_meta_html(
        "Tom's Squat", "3 reps · 225 lbs",
        "https://storage.googleapis.com/b/og-cards/abc.png",
        "https://frontend/challenges/c/participants/p/video/v",
        "lift",
    )
    assert 'property="og:title"' in html_doc
    assert 'property="og:description"' in html_doc
    assert 'property="og:image"' in html_doc
    assert 'og-cards/abc.png' in html_doc
    assert 'name="twitter:card" content="summary_large_image"' in html_doc
    # Human fallback: refresh + JS redirect to the target.
    assert "http-equiv=\"refresh\"" in html_doc
    assert "video/v" in html_doc


def test_render_meta_html_without_image_omits_image_tag():
    html_doc = og_card.render_meta_html("T", "D", None, "https://f/x", "golf")
    assert 'property="og:image"' not in html_doc
    assert 'property="og:title"' in html_doc


def test_render_meta_html_escapes_title():
    html_doc = og_card.render_meta_html(
        '<script>alert(1)</script>', "d & more", None, "https://f/x", "lift"
    )
    # The attacker-supplied title must be HTML-escaped, not reflected raw.
    assert "<script>alert(1)</script>" not in html_doc
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html_doc
    assert "d &amp; more" in html_doc


# --- crawler detection (pure helper on the route module) -------------------

def test_is_crawler_matches_known_bots():
    assert _is_crawler("Slackbot-LinkExpanding 1.0 (+https://api.slack.com/robots)")
    assert _is_crawler("facebookexternalhit/1.1")
    assert _is_crawler("Twitterbot/1.0")
    assert _is_crawler("Mozilla/5.0 (compatible; Discordbot/2.0)")


def test_is_crawler_ignores_humans_and_empty():
    assert not _is_crawler("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) Safari/605.1.15")
    assert not _is_crawler("")
    assert not _is_crawler(None)
