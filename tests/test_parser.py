from __future__ import annotations


from skillcheck.parser import parse_skill, discover_skills, _split_frontmatter


class TestSplitFrontmatter:
    def test_valid_frontmatter(self):
        text = "---\nname: foo\ndescription: bar\n---\n\nBody here."
        fm, body, offset, error = _split_frontmatter(text)
        assert error is None
        assert fm == {"name": "foo", "description": "bar"}
        assert "Body here." in body
        assert offset == 4

    def test_missing_opening_delimiter(self):
        text = "name: foo\n---\nBody"
        fm, body, offset, error = _split_frontmatter(text)
        assert error is not None
        assert "opening" in error

    def test_missing_closing_delimiter(self):
        text = "---\nname: foo\nBody without closing"
        fm, body, offset, error = _split_frontmatter(text)
        assert error is not None
        assert "closing" in error

    def test_invalid_yaml(self):
        text = "---\nname: [invalid: yaml: {{{\n---\nBody"
        fm, body, offset, error = _split_frontmatter(text)
        assert error is not None
        assert "invalid YAML" in error

    def test_empty_frontmatter(self):
        text = "---\n---\nBody"
        fm, body, offset, error = _split_frontmatter(text)
        assert error is None
        assert fm == {}
        assert "Body" in body

    def test_non_dict_frontmatter(self):
        text = "---\n- item1\n- item2\n---\nBody"
        fm, body, offset, error = _split_frontmatter(text)
        assert error is not None
        assert "mapping" in error

    def test_body_line_offset(self):
        text = "---\nname: test\n---\nline one\nline two"
        fm, body, offset, error = _split_frontmatter(text)
        assert error is None
        assert offset == 3


class TestParseSkill:
    def test_valid_minimal(self, fixture_path):
        info = parse_skill(fixture_path("valid-minimal"))
        assert info.parse_error is None
        assert info.frontmatter is not None
        assert info.frontmatter["name"] == "valid-minimal"
        assert "description" in info.frontmatter
        assert info.dir_name == "valid-minimal"
        assert len(info.body.strip()) > 0

    def test_valid_full(self, fixture_path):
        info = parse_skill(fixture_path("valid-full"))
        assert info.parse_error is None
        assert info.frontmatter["name"] == "valid-full"
        assert info.frontmatter["license"] == "MIT"
        assert "metadata" in info.frontmatter
        assert info.frontmatter["metadata"]["author"] == "test-author"
        assert "allowed-tools" in info.frontmatter

    def test_missing_skillmd(self, fixture_path):
        info = parse_skill(fixture_path("missing-skillmd"))
        assert info.parse_error == "SKILL.md not found"
        assert info.frontmatter is None

    def test_bad_frontmatter(self, fixture_path):
        info = parse_skill(fixture_path("bad-frontmatter"))
        assert info.parse_error is not None
        assert "invalid YAML" in info.parse_error

    def test_dir_name_extraction(self, fixture_path):
        info = parse_skill(fixture_path("valid-minimal"))
        assert info.dir_name == "valid-minimal"


class TestDiscoverSkills:
    def test_discovers_skills_in_fixtures(self, fixtures_dir):
        dirs = discover_skills(fixtures_dir)
        dir_names = [d.name for d in dirs]
        assert "valid-minimal" in dir_names
        assert "valid-full" in dir_names

    def test_does_not_include_non_skill_dirs(self, tmp_path):
        (tmp_path / "not-a-skill").mkdir()
        (tmp_path / "not-a-skill" / "README.md").write_text("hello")
        dirs = discover_skills(tmp_path)
        assert len(dirs) == 0

    def test_discovers_skill_with_skillmd(self, tmp_path):
        skill_dir = tmp_path / "my-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text("---\nname: my-skill\n---\nBody")
        dirs = discover_skills(tmp_path)
        assert len(dirs) == 1
        assert dirs[0].name == "my-skill"

    def test_discovers_children_of_skills_dir(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        child = skills_dir / "orphan-skill"
        child.mkdir()
        dirs = discover_skills(tmp_path)
        assert any(d.name == "orphan-skill" for d in dirs)
