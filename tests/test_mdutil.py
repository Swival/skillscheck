"""Unit tests for markdown slug generation, kept in step with markdownlint MD051."""

from skillscheck.mdutil import extract_headings, slugify_heading


class TestSlugifyHeading:
    def test_plain_words(self):
        assert slugify_heading("Installation") == "installation"
        assert slugify_heading("How to Use This Guide") == "how-to-use-this-guide"

    def test_inline_code_keeps_visible_text(self):
        # markdownlint renders inline code as its text: backticks drop, content stays.
        assert slugify_heading("Core Cache API (`xqd_cache.go`)") == "core-cache-api-xqd_cachego"
        assert (
            slugify_heading("HTTP Cache API (`xqd_http_cache.go`)")
            == "http-cache-api-xqd_http_cachego"
        )

    def test_em_dash_leaves_double_hyphen(self):
        # Removing the em dash leaves two adjacent spaces, which become two hyphens
        # (whitespace runs are not collapsed, matching markdownlint).
        assert (
            slugify_heading("Test Examples — Real VCL Patterns")
            == "test-examples--real-vcl-patterns"
        )

    def test_parentheses_dropped(self):
        assert slugify_heading("AST (Abstract Syntax Tree)") == "ast-abstract-syntax-tree"

    def test_link_reduced_to_text(self):
        assert slugify_heading("See [the docs](https://example.com)") == "see-the-docs"


class TestExtractHeadings:
    def test_inline_code_heading_slug(self):
        text = "# Title\n\n### Core Cache API (`xqd_cache.go`)\n"
        assert "core-cache-api-xqd_cachego" in extract_headings(text)

    def test_heading_inside_fenced_block_ignored(self):
        text = "# Real\n\n```\n### Fake Heading\n```\n"
        slugs = extract_headings(text)
        assert "real" in slugs
        assert "fake-heading" not in slugs
