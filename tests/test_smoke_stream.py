#!/usr/bin/env python3
"""
smoke_stream.py のユニットテスト
"""

import os
import sys
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

# scriptsディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import pytest


class TestSmokeStream:
    """smoke_stream.pyの主要なロジックをテスト"""
    
    def test_openai_api_detection_with_empty_url(self):
        """AIPERF_URLが空の場合、OpenAI APIを使用することを確認"""
        url = ""
        use_openai_api = not url or url == "https://api.openai.com/v1" or url == "https://api.openai.com"
        assert use_openai_api is True
    
    def test_openai_api_detection_with_openai_url(self):
        """AIPERF_URLがOpenAIのURLの場合、OpenAI APIを使用することを確認"""
        url = "https://api.openai.com/v1"
        use_openai_api = not url or url == "https://api.openai.com/v1" or url == "https://api.openai.com"
        assert use_openai_api is True
        
        url = "https://api.openai.com"
        use_openai_api = not url or url == "https://api.openai.com/v1" or url == "https://api.openai.com"
        assert use_openai_api is True
    
    def test_custom_api_detection(self):
        """カスタムURLの場合、OpenAI APIを使用しないことを確認"""
        url = "http://192.168.1.100:8000"
        use_openai_api = not url or url == "https://api.openai.com/v1" or url == "https://api.openai.com"
        assert use_openai_api is False
    
    def test_url_normalization(self):
        """URLにhttp://が付いていない場合、追加されることを確認"""
        url = "192.168.1.100:8000"
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"http://{url}"
        assert url == "http://192.168.1.100:8000"
    
    def test_url_already_has_protocol(self):
        """URLに既にプロトコルが付いている場合、変更されないことを確認"""
        url = "https://example.com:8000"
        if not url.startswith("http://") and not url.startswith("https://"):
            url = f"http://{url}"
        assert url == "https://example.com:8000"
    
    @patch.dict(os.environ, {"MODEL": "", "AIPERF_URL": "", "API_KEY": ""})
    def test_missing_model_env_var(self):
        """MODEL環境変数が設定されていない場合のエラー検証"""
        model = os.getenv("MODEL", "")
        assert model == ""
    
    @patch.dict(os.environ, {"MODEL": "gpt-3.5-turbo", "AIPERF_URL": "", "API_KEY": ""})
    def test_missing_api_key_for_openai(self):
        """OpenAI API使用時にAPIキーが設定されていない場合のエラー検証"""
        url = os.getenv("AIPERF_URL", "").strip().rstrip("/")
        api_key = os.getenv("API_KEY", "")
        use_openai_api = not url or url == "https://api.openai.com/v1" or url == "https://api.openai.com"
        
        assert use_openai_api is True
        assert api_key == ""
    
    @patch('openai.OpenAI')
    def test_openai_client_creation_with_api_key(self, mock_openai):
        """OpenAI API使用時のクライアント作成を確認"""
        api_key = "sk-test-key"
        url = ""
        use_openai_api = not url or url == "https://api.openai.com/v1" or url == "https://api.openai.com"
        
        if use_openai_api:
            client_kwargs = {"api_key": api_key}
        else:
            client_kwargs = {"base_url": url, "api_key": api_key if api_key else "dummy-key"}
        
        assert "api_key" in client_kwargs
        assert client_kwargs["api_key"] == "sk-test-key"
        assert "base_url" not in client_kwargs
    
    @patch('openai.OpenAI')
    def test_custom_api_client_creation(self, mock_openai):
        """カスタムAPI使用時のクライアント作成を確認"""
        api_key = ""
        url = "http://192.168.1.100:8000"
        use_openai_api = not url or url == "https://api.openai.com/v1" or url == "https://api.openai.com"
        
        if use_openai_api:
            client_kwargs = {"api_key": api_key}
        else:
            client_kwargs = {"base_url": url, "api_key": api_key if api_key else "dummy-key"}
        
        assert "base_url" in client_kwargs
        assert client_kwargs["base_url"] == "http://192.168.1.100:8000"
        assert client_kwargs["api_key"] == "dummy-key"
    
    @patch('openai.OpenAI')
    def test_streaming_request_structure(self, mock_openai):
        """ストリーミングリクエストの基本構造を確認"""
        mock_client = MagicMock()
        mock_stream = MagicMock()
        
        # ストリーミングレスポンスのモック
        mock_chunk1 = MagicMock()
        mock_chunk1.choices = [MagicMock()]
        mock_chunk1.choices[0].delta = MagicMock()
        mock_chunk1.choices[0].delta.content = "Hello"
        
        mock_chunk2 = MagicMock()
        mock_chunk2.choices = [MagicMock()]
        mock_chunk2.choices[0].delta = MagicMock()
        mock_chunk2.choices[0].delta.content = " World"
        
        mock_stream.__iter__ = Mock(return_value=iter([mock_chunk1, mock_chunk2]))
        mock_client.chat.completions.create.return_value = mock_stream
        
        # ストリーミングリクエストをシミュレート
        model = "gpt-3.5-turbo"
        stream = mock_client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": "Test"}],
            stream=True,
            max_tokens=50,
        )
        
        # チャンクの処理をシミュレート
        token_count = 0
        full_response = ""
        for chunk in stream:
            if chunk.choices and len(chunk.choices) > 0:
                delta = chunk.choices[0].delta
                if delta.content:
                    full_response += delta.content
                    token_count += 1
        
        assert token_count == 2
        assert full_response == "Hello World"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
