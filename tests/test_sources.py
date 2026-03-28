from unittest.mock import patch, MagicMock

from finder.models import ImageCandidate
from finder.sources import genius, spotify, duckduckgo


class TestGeniusSource:
    @patch("lyricsgenius.Genius")
    def test_search_returns_images(self, mock_genius_cls):
        mock_artist = MagicMock()
        mock_artist.header_image_url = "https://example.com/header.jpg"
        mock_artist.image_url = "https://example.com/profile.jpg"

        mock_genius = MagicMock()
        mock_genius.search_artist.return_value = mock_artist
        mock_genius_cls.return_value = mock_genius

        results = genius.search("Drake", token="fake_token")

        assert len(results) == 2
        assert all(isinstance(r, ImageCandidate) for r in results)
        assert results[0].source == "genius"
        assert results[0].url == "https://example.com/header.jpg"

    @patch("lyricsgenius.Genius")
    def test_search_artist_not_found(self, mock_genius_cls):
        mock_genius = MagicMock()
        mock_genius.search_artist.return_value = None
        mock_genius_cls.return_value = mock_genius

        results = genius.search("nonexistentartist12345", token="fake_token")
        assert results == []

    @patch("lyricsgenius.Genius")
    def test_search_deduplicates_same_url(self, mock_genius_cls):
        mock_artist = MagicMock()
        mock_artist.header_image_url = "https://example.com/same.jpg"
        mock_artist.image_url = "https://example.com/same.jpg"

        mock_genius = MagicMock()
        mock_genius.search_artist.return_value = mock_artist
        mock_genius_cls.return_value = mock_genius

        results = genius.search("Drake", token="fake_token")
        assert len(results) == 1


class TestSpotifySource:
    @patch("spotipy.Spotify")
    @patch("finder.sources.spotify.SpotifyClientCredentials")
    def test_search_returns_images(self, mock_auth, mock_sp_cls):
        mock_sp = MagicMock()
        mock_sp.search.return_value = {
            "artists": {
                "items": [{
                    "popularity": 90,
                    "images": [
                        {"url": "https://i.scdn.co/image/large.jpg"},
                        {"url": "https://i.scdn.co/image/medium.jpg"},
                    ]
                }]
            }
        }
        mock_sp_cls.return_value = mock_sp

        results = spotify.search("Drake", client_id="id", client_secret="secret")

        assert len(results) == 2
        assert all(r.source == "spotify" for r in results)

    @patch("spotipy.Spotify")
    @patch("finder.sources.spotify.SpotifyClientCredentials")
    def test_search_no_results(self, mock_auth, mock_sp_cls):
        mock_sp = MagicMock()
        mock_sp.search.return_value = {"artists": {"items": []}}
        mock_sp_cls.return_value = mock_sp

        results = spotify.search("nonexistent", client_id="id", client_secret="secret")
        assert results == []

    @patch("spotipy.Spotify")
    @patch("finder.sources.spotify.SpotifyClientCredentials")
    def test_picks_highest_popularity(self, mock_auth, mock_sp_cls):
        mock_sp = MagicMock()
        mock_sp.search.return_value = {
            "artists": {
                "items": [
                    {"popularity": 30, "images": [{"url": "https://low.jpg"}]},
                    {"popularity": 95, "images": [{"url": "https://high.jpg"}]},
                ]
            }
        }
        mock_sp_cls.return_value = mock_sp

        results = spotify.search("Drake", client_id="id", client_secret="secret")
        assert results[0].url == "https://high.jpg"


class TestDuckDuckGoSource:
    @patch("finder.sources.duckduckgo.DDGS")
    @patch("finder.sources.duckduckgo.time")
    def test_search_returns_candidates(self, mock_time, mock_ddgs_class):
        mock_ddgs = MagicMock()
        mock_ddgs.images.return_value = [
            {"image": "https://example.com/1.jpg"},
            {"image": "https://example.com/2.jpg"},
        ]
        mock_ddgs_class.return_value = mock_ddgs

        results = duckduckgo.search("Drake", max_results=10)

        assert len(results) == 2
        assert all(r.source == "duckduckgo" for r in results)

    @patch("finder.sources.duckduckgo.DDGS")
    @patch("finder.sources.duckduckgo.time")
    def test_search_deduplicates_urls(self, mock_time, mock_ddgs_class):
        mock_ddgs = MagicMock()
        mock_ddgs.images.return_value = [
            {"image": "https://example.com/same.jpg"},
            {"image": "https://example.com/same.jpg"},
            {"image": "https://example.com/different.jpg"},
        ]
        mock_ddgs_class.return_value = mock_ddgs

        results = duckduckgo.search("Drake")
        assert len(results) == 2

    @patch("finder.sources.duckduckgo.DDGS")
    @patch("finder.sources.duckduckgo.time")
    def test_search_empty_results(self, mock_time, mock_ddgs_class):
        mock_ddgs = MagicMock()
        mock_ddgs.images.return_value = []
        mock_ddgs_class.return_value = mock_ddgs

        results = duckduckgo.search("unknown person xyz")
        assert results == []
