"""Tests for STT punctuation restoration and LLM client endpoint ordering."""

from app.services.stt_service import _restore_punctuation


class TestRestorePunctuation:
    def test_empty_text(self):
        assert _restore_punctuation("") == ""

    def test_short_text_untouched(self):
        assert _restore_punctuation("你好") == "你好"

    def test_adds_period_at_end(self):
        result = _restore_punctuation("我使用了 Transformer 做文本分类")
        assert result.endswith("。")

    def test_adds_comma_before_connective(self):
        text = "我用了 RAG然后又加了 Agent 编排"
        result = _restore_punctuation(text)
        assert "，然后" in result

    def test_multiple_connectives(self):
        text = "首先我设计了数据模型然后实现了 API 接口最后部署到 K8s 上"
        result = _restore_punctuation(text)
        assert "，然后" in result
        assert "，最后" in result

    def test_already_punctuated_not_modified(self):
        text = "我用了 Transformer，然后加了 RAG 检索。最终效果很好。"
        result = _restore_punctuation(text)
        # Should not double-punctuate
        assert "，，" not in result

    def test_does_not_add_leading_comma(self):
        text = "然后我使用了异步处理方案"
        result = _restore_punctuation(text)
        assert not result.startswith("，")

    def test_chinese_english_mixed(self):
        text = "我在项目中用了 Docker 部署但是遇到了网络问题所以改用了 host 模式"
        result = _restore_punctuation(text)
        assert "，但是" in result
        assert "，所以" in result

    def test_ends_with_comma_replaced_by_period(self):
        # If last char after processing is comma, it should become period
        text = "我用了 Redis 做缓存另外"
        result = _restore_punctuation(text)
        assert result.endswith("。") or result.endswith("另外。")

    def test_preserves_question_marks(self):
        text = "你知道 GMP 调度模型吗？"
        result = _restore_punctuation(text)
        assert result.endswith("？")


class TestLLMClientEndpoints:
    def test_endpoint_order_standard_base(self):
        from app.services.llm_client import RelayLLMClient

        client = RelayLLMClient.__new__(RelayLLMClient)
        client.base_url = "https://api.example.com"
        client.api_key = "test"
        endpoints = client._candidate_endpoints()
        # Only the /v1/ path should be returned (no bogus fallback)
        assert len(endpoints) == 1
        assert endpoints[0] == "https://api.example.com/v1/chat/completions"

    def test_endpoint_order_v1_suffix(self):
        from app.services.llm_client import RelayLLMClient

        client = RelayLLMClient.__new__(RelayLLMClient)
        client.base_url = "https://api.example.com/v1"
        client.api_key = "test"
        endpoints = client._candidate_endpoints()
        assert len(endpoints) == 1
        assert endpoints[0] == "https://api.example.com/v1/chat/completions"

    def test_endpoint_empty_base(self):
        from app.services.llm_client import RelayLLMClient

        client = RelayLLMClient.__new__(RelayLLMClient)
        client.base_url = ""
        client.api_key = "test"
        assert client._candidate_endpoints() == []
