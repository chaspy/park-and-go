import pytest

from app.sources.official_site import (
    _find_mentions,
    _extract_text,
    _candidate_urls,
    _deduplicate_mentions,
    ParkingMention,
)


class TestFindMentions:
    def test_positive_parking_ari(self):
        mentions = _find_mentions("当店には駐車場ありです。お気軽にお越しください。")
        assert any(m.kind == "positive" for m in mentions)

    def test_positive_senyo(self):
        mentions = _find_mentions("専用駐車場をご用意しております。")
        assert any(m.kind == "positive" for m in mentions)

    def test_partner(self):
        mentions = _find_mentions("近くに提携駐車場がございます。サービス券をお渡しします。")
        assert any(m.kind == "partner" for m in mentions)
        assert sum(1 for m in mentions if m.kind == "partner") >= 1

    def test_negative_nashi(self):
        mentions = _find_mentions("申し訳ございませんが、駐車場はありません。")
        assert any(m.kind == "negative" for m in mentions)

    def test_negative_enryo(self):
        mentions = _find_mentions("お車でのご来店はご遠慮ください。")
        assert any(m.kind == "negative" for m in mentions)

    def test_negative_coin_parking(self):
        mentions = _find_mentions("近隣のコインパーキングをご利用ください。")
        assert any(m.kind == "negative" for m in mentions)

    def test_capacity(self):
        mentions = _find_mentions("駐車場: 10台")
        cap = [m for m in mentions if m.kind == "capacity"]
        assert len(cap) == 1
        assert cap[0].value == "10"

    def test_height_limit_vehicle(self):
        """車高 prefix should always match."""
        mentions = _find_mentions("車高制限: 1.55m")
        lim = [m for m in mentions if m.kind == "height_limit"]
        assert len(lim) == 1
        assert lim[0].value == "1.55"

    def test_width_limit_vehicle(self):
        """車幅 prefix should always match."""
        mentions = _find_mentions("車幅制限: 1.85m")
        lim = [m for m in mentions if m.kind == "width_limit"]
        assert len(lim) == 1
        assert lim[0].value == "1.85"

    def test_height_limit_contextual(self):
        """高さ without 車 prefix should only match near parking context."""
        text = "立体駐車場のため高さ制限: 2.1mとなっております。"
        mentions = _find_mentions(text)
        lim = [m for m in mentions if m.kind == "height_limit"]
        assert len(lim) == 1
        assert lim[0].value == "2.1"

    def test_height_no_parking_context_ignored(self):
        """高さ without parking context should NOT match (e.g. furniture)."""
        text = "【スチール棚】幅35cm、奥行き30cm、高さ41cm（最下段のみ46cm）"
        mentions = _find_mentions(text)
        lim = [m for m in mentions if m.kind in ("height_limit", "width_limit")]
        assert len(lim) == 0

    def test_bookshelf_dimensions_not_matched(self):
        """Bookshelf/furniture dimensions must not be treated as parking limits."""
        text = (
            "本棚 随時増枠中・参加可能です。"
            "【スチール棚】 幅35cm、奥行き30cm、高さ41cm（最下段のみ46cm）。"
            "【木棚】 幅38cm、奥行26cm、高さ30cm前後"
        )
        mentions = _find_mentions(text)
        lim = [m for m in mentions if m.kind in ("height_limit", "width_limit")]
        assert len(lim) == 0

    def test_tight_kei_only(self):
        mentions = _find_mentions("軽自動車推奨の駐車場です。")
        assert any(m.kind == "tight" for m in mentions)

    def test_tight_narrow(self):
        mentions = _find_mentions("駐車場は狭いのでご注意ください。")
        assert any(m.kind == "tight" for m in mentions)

    def test_narrow_without_parking_not_matched(self):
        """Just '狭い' without parking context should not match."""
        mentions = _find_mentions("店内は少し狭いですがご了承ください。")
        assert not any(m.kind == "tight" for m in mentions)

    def test_no_mention(self):
        mentions = _find_mentions("当店は美味しいラーメン屋です。営業時間は11時から22時まで。")
        assert len(mentions) == 0

    def test_english_free_parking(self):
        mentions = _find_mentions("We offer free parking for all customers.")
        assert any(m.kind == "positive" for m in mentions)


class TestDeduplication:
    def test_removes_exact_duplicates(self):
        mentions = [
            ParkingMention(text="駐車場あり", context="ctx1", kind="positive"),
            ParkingMention(text="駐車場あり", context="ctx2", kind="positive"),
            ParkingMention(text="提携駐車場", context="ctx3", kind="partner"),
        ]
        result = _deduplicate_mentions(mentions)
        assert len(result) == 2

    def test_keeps_different_kinds(self):
        mentions = [
            ParkingMention(text="駐車場", context="ctx1", kind="positive"),
            ParkingMention(text="駐車場", context="ctx2", kind="negative"),
        ]
        result = _deduplicate_mentions(mentions)
        assert len(result) == 2


class TestExtractText:
    def test_removes_script_style(self):
        html = "<html><script>var x=1;</script><style>.a{}</style><p>Hello</p></html>"
        text = _extract_text(html)
        assert "var x" not in text
        assert "Hello" in text


class TestCandidateUrls:
    def test_generates_access_paths(self):
        urls = _candidate_urls("https://example.com")
        assert "https://example.com" in urls
        assert "https://example.com/access" in urls
        assert "https://example.com/shop" in urls
        assert len(urls) > 5
