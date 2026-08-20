"""Unit tests for the markdown helpers: slugs, headings, and bold field labels.

Slug generation is kept in step with markdownlint MD051.
"""

from skillscheck.mdutil import (
    StrongLabel,
    collect_strong_labels,
    extract_headings,
    slugify_heading,
)


class TestSlugifyHeading:
    def test_plain_words(self):
        assert slugify_heading("Installation") == "installation"
        assert slugify_heading("How to Use This Guide") == "how-to-use-this-guide"

    def test_inline_code_keeps_visible_text(self):
        # markdownlint renders inline code as its text: backticks drop, content stays.
        assert (
            slugify_heading("Core Cache API (`xqd_cache.go`)")
            == "core-cache-api-xqd_cachego"
        )
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
        assert (
            slugify_heading("AST (Abstract Syntax Tree)") == "ast-abstract-syntax-tree"
        )

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


class TestCollectStrongLabels:
    def test_paragraph_and_list_item_labels(self):
        text = (
            "**Repo:** one\n"
            "\n"
            "__Source:__ two\n"
            "\n"
            "- **Owner:** three\n"
            "\n"
            "- __Since:__ four\n"
        )
        assert collect_strong_labels(text) == {
            "repo": StrongLabel(count=1, first_line=1),
            "source": StrongLabel(count=1, first_line=3),
            "owner": StrongLabel(count=1, first_line=5),
            "since": StrongLabel(count=1, first_line=7),
        }

    def test_counts_keep_the_first_line(self):
        text = "- **Repo:** a\n- **Repo:** b\n- **Repo:** c\n"
        assert collect_strong_labels(text) == {
            "repo": StrongLabel(count=3, first_line=1)
        }

    def test_case_and_pre_colon_space_normalized(self):
        text = "- **Repo:** a\n- **REPO :** b\n- **repo   :** c\n"
        assert collect_strong_labels(text) == {
            "repo": StrongLabel(count=3, first_line=1)
        }

    def test_internal_whitespace_collapsed(self):
        text = "- **Last  verified:** a\n- **Last verified:** b\n"
        assert collect_strong_labels(text) == {
            "last verified": StrongLabel(count=2, first_line=1)
        }

    def test_span_later_in_a_sentence_is_not_a_label(self):
        assert collect_strong_labels("Read this. **Note:** it matters.\n") == {}

    def test_paragraph_continuation_is_not_a_label(self):
        assert collect_strong_labels("First line.\n**Note:** second line.\n") == {}

    def test_label_of_more_than_four_words_ignored(self):
        assert collect_strong_labels("**One two three four five:** a\n") == {}

    def test_strong_text_without_a_colon_ignored(self):
        assert collect_strong_labels("- **Repo** a\n") == {}

    def test_double_asterisk_may_touch_a_word(self):
        assert collect_strong_labels("**Repo:**value\n") == {
            "repo": StrongLabel(count=1, first_line=1)
        }

    def test_underscore_emphasis_inside_a_word_rejected(self):
        assert collect_strong_labels("__Repo:__value\n") == {}

    def test_blockquote_prefix_removed(self):
        text = "> **Repo:** a\n>\n> - **Repo:** b\n"
        assert collect_strong_labels(text) == {
            "repo": StrongLabel(count=2, first_line=1)
        }

    def test_nested_blockquote_keeps_physical_lines(self):
        text = "Intro.\n\n> > - **Repo:** a\n> > - **Source:** b\n"
        assert collect_strong_labels(text) == {
            "repo": StrongLabel(count=1, first_line=3),
            "source": StrongLabel(count=1, first_line=4),
        }

    def test_backtick_fence_hides_labels(self):
        text = "```\n- **Repo:** a\n- **Source:** b\n```\n"
        assert collect_strong_labels(text) == {}

    def test_tilde_fence_hides_labels(self):
        assert collect_strong_labels("~~~\n- **Repo:** a\n~~~\n") == {}

    def test_longer_closing_fence_closes_the_block(self):
        text = "```\ncode\n````\n\n- **Repo:** a\n"
        assert collect_strong_labels(text) == {
            "repo": StrongLabel(count=1, first_line=5)
        }

    def test_short_or_mismatched_closer_keeps_the_block_open(self):
        text = "````\n```\n- **Repo:** a\n~~~\n- **Source:** b\n"
        assert collect_strong_labels(text) == {}

    def test_closer_with_trailing_text_does_not_close(self):
        text = "```\ncode\n```js\n- **Repo:** a\n```\n\n- **Source:** b\n"
        assert collect_strong_labels(text) == {
            "source": StrongLabel(count=1, first_line=7)
        }

    def test_fenced_schema_inside_a_blockquote_ignored(self):
        text = "> ```markdown\n> - **Repo:** a\n> - **Source:** b\n> ```\n"
        assert collect_strong_labels(text) == {}

    def test_indented_code_ignored(self):
        text = "Intro.\n\n    - **Repo:** a\n\n- **Source:** b\n"
        assert collect_strong_labels(text) == {
            "source": StrongLabel(count=1, first_line=5)
        }

    def test_inline_code_ignored(self):
        assert collect_strong_labels("`**Repo:**` a\n") == {}

    def test_escaped_delimiter_ignored(self):
        assert collect_strong_labels("\\**Repo:** a\n") == {}

    def test_table_cell_is_not_a_label(self):
        text = "| **Repo:** | a |\n| **Repo:** | b |\n"
        assert collect_strong_labels(text) == {}

    def test_heading_is_not_a_label_line(self):
        text = "## **Repo:** a\n\n**Repo:** b\n"
        assert collect_strong_labels(text) == {
            "repo": StrongLabel(count=1, first_line=3)
        }

    def test_setext_h1_underline_makes_a_heading(self):
        text = "**Repo:**\n===\n\n**Repo:**\n===\n"
        assert collect_strong_labels(text) == {}

    def test_setext_h2_underline_makes_a_heading(self):
        text = "**Repo:**\n---------\n\n**Repo:**\n---------\n"
        assert collect_strong_labels(text) == {}

    def test_quoted_setext_underline_makes_a_heading(self):
        text = "> **Repo:**\n> ---\n>\n> **Repo:**\n> ---\n"
        assert collect_strong_labels(text) == {}

    def test_dashes_under_a_list_item_stay_a_thematic_break(self):
        text = "- **Repo:** a\n---\n\n- **Repo:** b\n"
        assert collect_strong_labels(text) == {
            "repo": StrongLabel(count=2, first_line=1)
        }

    def test_thematic_break_is_not_a_label_line(self):
        text = "- **Repo:** a\n\n***\n\n- **Repo:** b\n"
        assert collect_strong_labels(text) == {
            "repo": StrongLabel(count=2, first_line=1)
        }
