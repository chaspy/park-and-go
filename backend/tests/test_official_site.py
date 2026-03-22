import pytest

from app.sources.official_site import _find_mentions, _extract_text, _candidate_urls


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

    def test_height_limit(self):
        mentions = _find_mentions("車高制限: 1.55m")
        lim = [m for m in mentions if m.kind == "height_limit"]
        assert len(lim) == 1
        assert lim[0].value == "1.55"

    def test_width_limit(self):
        mentions = _find_mentions("車幅制限: 1.85m")
        lim = [m for m in mentions if m.kind == "width_limit"]
        assert len(lim) == 1
        assert lim[0].value == "1.85"

    def test_tight_kei_only(self):
        mentions = _find_mentions("軽自動車推奨の駐車場です。")
        assert any(m.kind == "tight" for m in mentions)

    def test_tight_narrow(self):
        mentions = _find_mentions("駐車場は狭いのでご注意ください。")
        assert any(m.kind == "tight" for m in mentions)

    def test_no_mention(self):
        mentions = _find_mentions("当店は美味しいラーメン屋です。営業時間は11時から22時まで。")
        assert len(mentions) == 0

    def test_english_free_parking(self):
        mentions = _find_mentions("We offer free parking for all customers.")
        assert any(m.kind == "positive" for m in mentions)


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
