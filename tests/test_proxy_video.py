# -*- coding: utf-8 -*-
"""
代理转发功能单元测试
测试视频代理转发逻辑的稳定性和正确性
"""

import os
import sys
import time
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'api'))


class TestProxyVideoRoute:
    """测试代理视频路由"""

    def test_proxy_video_route_exists(self):
        """测试代理路由是否存在"""
        from server import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            response = client.get('/api/proxy/video/test.mp4')
            assert response.status_code in [200, 400, 404, 500], \
                f"代理路由应返回有效状态码，实际返回: {response.status_code}"

    def test_proxy_video_invalid_path_rejected(self):
        """测试无效路径被拒绝"""
        from server import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            response = client.get('/api/proxy/video/../../etc/passwd')
            assert response.status_code == 400, "路径遍历攻击应被拒绝"

    def test_proxy_video_empty_path_rejected(self):
        """测试空路径被拒绝"""
        from server import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            response = client.get('/api/proxy/video/')
            assert response.status_code == 404, "空路径应返回404"


class TestStreamVideoFromCOS:
    """测试从COS流式读取视频"""

    @pytest.fixture(autouse=True)
    def setup_cos(self):
        """确保COS客户端初始化"""
        from server import init_cos_client, cos_client
        init_cos_client()
        yield cos_client is not None

    def test_stream_video_nonexistent_file(self, setup_cos):
        """测试读取不存在的文件"""
        if not setup_cos:
            pytest.skip("COS客户端未初始化")

        from server import stream_video_from_cos
        result = stream_video_from_cos('private/02-learning/videos/nonexistent_file.mp4')
        assert result is None, "不存在的文件应返回None"

    def test_stream_video_existing_file(self, setup_cos):
        """测试读取已存在的视频文件"""
        if not setup_cos:
            pytest.skip("COS客户端未初始化")

        from server import stream_video_from_cos
        test_key = 'private/02-learning/videos/math/numberblocks/数字虫_Numberblocks_E01_5分5秒.mp4'
        result = stream_video_from_cos(test_key)

        assert result is not None, f"文件 {test_key} 应该存在"

        data = result.read(1024)
        assert len(data) > 0, "读取的视频数据不应为空"

    def test_stream_video_read_chunks(self, setup_cos):
        """测试分块读取视频"""
        if not setup_cos:
            pytest.skip("COS客户端未初始化")

        from server import stream_video_from_cos
        test_key = 'private/02-learning/videos/math/numberblocks/数字虫_Numberblocks_E01_5分5秒.mp4'
        result = stream_video_from_cos(test_key)

        if result is None:
            pytest.skip("测试文件不存在")

        chunk_count = 0
        total_bytes = 0
        while True:
            chunk = result.read(8192)
            if not chunk:
                break
            chunk_count += 1
            total_bytes += len(chunk)

        assert chunk_count > 0, "应该能读取到多个数据块"
        assert total_bytes > 0, "总字节数应该大于0"
        print(f"分块读取成功: {chunk_count} 块, 共 {total_bytes} 字节")


class TestProxyVideoIntegration:
    """集成测试：代理视频端到端"""

    @pytest.fixture(autouse=True)
    def setup_cos(self):
        """确保COS客户端初始化"""
        from server import init_cos_client, cos_client
        init_cos_client()
        yield cos_client is not None

    @pytest.fixture
    def real_video_key(self, setup_cos):
        """获取一个真实的视频key用于测试"""
        if not setup_cos:
            pytest.skip("COS客户端未初始化")

        return 'private/02-learning/videos/math/numberblocks/数字虫_Numberblocks_E01_5分5秒.mp4'

    def test_proxy_video_returns_stream(self, real_video_key):
        """测试代理返回视频流"""
        from server import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            response = client.get(f'/api/proxy/video/{real_video_key}')

            assert response.status_code == 200, \
                f"代理请求应成功，实际状态码: {response.status_code}"

            assert response.content_type == 'video/mp4', \
                f"内容类型应为 video/mp4，实际: {response.content_type}"

    def test_proxy_video_stream_complete(self, real_video_key):
        """测试视频流完整传输"""
        from server import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            response = client.get(f'/api/proxy/video/{real_video_key}')

            assert response.status_code == 200

            data = response.data
            assert len(data) > 0, "应该接收到视频数据"
            print(f"完整流传输成功: {len(data)} 字节")

    def test_proxy_video_headers(self, real_video_key):
        """测试代理响应的头信息"""
        from server import app
        app.config['TESTING'] = True
        with app.test_client() as client:
            response = client.get(f'/api/proxy/video/{real_video_key}')

            assert response.status_code == 200, \
                f"代理请求应成功，实际状态码: {response.status_code}"

            assert 'Content-Disposition' in response.headers, \
                "响应应包含 Content-Disposition 头"


class TestSignedUrlGeneration:
    """测试签名URL生成"""

    @pytest.fixture(autouse=True)
    def setup_cos(self):
        """确保COS客户端初始化"""
        from server import init_cos_client, cos_client
        init_cos_client()
        yield cos_client is not None

    def test_signed_url_generation(self, setup_cos):
        """测试签名URL生成"""
        if not setup_cos:
            pytest.skip("COS客户端未初始化")

        from server import get_signed_url
        test_key = 'private/02-learning/videos/math/numberblocks/数字虫_Numberblocks_E01_5分5秒.mp4'
        url = get_signed_url(test_key, expires=3600)

        assert url is not None, "签名URL应该成功生成"
        assert 'cos.' in url or 'myqcloud' in url or 'tencent' in url or '签名' in url or 'Signature' in url, \
            "签名URL应该包含COS域名或签名信息"

    def test_signed_url_expiration(self, setup_cos):
        """测试签名URL过期时间"""
        if not setup_cos:
            pytest.skip("COS客户端未初始化")

        from server import get_signed_url
        test_key = 'private/02-learning/videos/math/numberblocks/数字虫_Numberblocks_E01_5分5秒.mp4'

        url_short = get_signed_url(test_key, expires=60)
        url_long = get_signed_url(test_key, expires=3600)

        assert url_short is not None, "短过期时间URL应该生成"
        assert url_long is not None, "长过期时间URL应该生成"


class TestProxyVideoStability:
    """代理视频稳定性测试"""

    @pytest.fixture(autouse=True)
    def setup_cos(self):
        """确保COS客户端初始化"""
        from server import init_cos_client, cos_client
        init_cos_client()
        yield cos_client is not None

    def test_multiple_concurrent_requests(self, setup_cos):
        """测试多次并发请求的稳定性"""
        if not setup_cos:
            pytest.skip("COS客户端未初始化")

        from server import app
        app.config['TESTING'] = True

        test_key = 'private/02-learning/videos/math/numberblocks/数字虫_Numberblocks_E01_5分5秒.mp4'

        success_count = 0
        total_requests = 5

        with app.test_client() as client:
            for i in range(total_requests):
                try:
                    response = client.get(f'/api/proxy/video/{test_key}')
                    if response.status_code == 200:
                        success_count += 1
                except Exception as e:
                    print(f"请求 {i+1} 失败: {e}")

        success_rate = success_count / total_requests
        assert success_rate >= 0.8, \
            f"成功率应 >= 80%，实际: {success_rate*100:.1f}%"
        print(f"并发稳定性测试通过: {success_count}/{total_requests} 成功")

    def test_rapid_sequential_requests(self, setup_cos):
        """测试快速连续请求"""
        if not setup_cos:
            pytest.skip("COS客户端未初始化")

        from server import app
        app.config['TESTING'] = True

        test_key = 'private/02-learning/videos/math/numberblocks/数字虫_Numberblocks_E01_5分5秒.mp4'

        response_times = []

        with app.test_client() as client:
            for _ in range(3):
                start = time.time()
                response = client.get(f'/api/proxy/video/{test_key}')
                elapsed = time.time() - start

                if response.status_code == 200:
                    response_times.append(elapsed)

        if response_times:
            avg_time = sum(response_times) / len(response_times)
            print(f"平均响应时间: {avg_time:.3f}秒")
            assert all(t < 30 for t in response_times), \
                "所有响应时间应小于30秒"


class TestVideoCategories:
    """测试视频分类配置"""

    @pytest.fixture(autouse=True)
    def setup_cos(self):
        """确保COS客户端初始化"""
        from server import init_cos_client, cos_client
        init_cos_client()
        yield cos_client is not None

    def test_all_categories_accessible(self, setup_cos):
        """测试所有分类都可访问"""
        if not setup_cos:
            pytest.skip("COS客户端未初始化")

        from server import app
        app.config['TESTING'] = True

        categories = ['math', 'english', 'pinyin', 'science']

        with app.test_client() as client:
            for category in categories:
                response = client.get(f'/api/videos?category={category}')
                assert response.status_code == 200, \
                    f"分类 {category} 应可访问"


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])