/**
 * Edge TTS for Browser
 * 使用微软Edge浏览器的TTS服务，无需API Key
 */
class EdgeTTS {
    constructor() {
        this.ws = null;
        this.audioChunks = [];
        this.voice = 'zh-CN-XiaoxiaoNeural'; // 默认晓晓女声
    }

    // 设置语音
    setVoice(voice) {
        this.voice = voice;
    }

    // 获取可用语音列表
    async getVoices() {
        try {
            const response = await fetch(
                'https://speech.platform.bing.com/consumer/speech/synthesize/readaloud/voices/list?trustedclientid=694BTJAU3XKHDTGAHII'
            );
            const text = await response.text();
            // 解析 voices
            const voices = [];
            const regex = /"Name":"([^"]+)".*?"Locale":"([^"]+)".*?"FriendlyName":"([^"]+)"/g;
            let match;
            while ((match = regex.exec(text)) !== null) {
                if (match[2].startsWith('zh-CN')) {
                    voices.push({
                        name: match[1],
                        locale: match[2],
                        friendlyName: match[3]
                    });
                }
            }
            return voices;
        } catch (e) {
            console.warn('获取语音列表失败:', e);
            return [];
        }
    }

    // 合成语音
    async speak(text) {
        return new Promise((resolve, reject) => {
            const wsUrl = 'wss://speech.platform.bing.com/consumer/speech/synthesize/readaloud/edge/v1?trustedclientid=694BTJAU3XKHDTGAHII';
            const ws = new WebSocket(wsUrl);
            this.audioChunks = [];

            ws.onopen = () => {
                // 发送配置
                const config = {
                    type: 'config',
                    audio: {
                        format: 'audio-24khz-48kbitrate-mono-mp3',
                        sampleRate: 24000
                    },
                    lang: 'zh-CN',
                    voice: this.voice,
                    name: this.voice,
                    rate: '-20%',   // 减慢20%
                    volume: '+0%',
                    pitch: '+0Hz'
                };
                ws.send(JSON.stringify(config));
            };

            ws.onmessage = (event) => {
                if (typeof event.data === 'string') {
                    // 文本响应
                    console.log('Edge TTS connected');
                } else {
                    // 二进制音频数据
                    this.audioChunks.push(event.data);
                }
            };

            ws.onerror = (error) => {
                console.error('WebSocket error:', error);
                reject(error);
            };

            ws.onclose = () => {
                if (this.audioChunks.length > 0) {
                    const blob = new Blob(this.audioChunks, { type: 'audio/mp3' });
                    const url = URL.createObjectURL(blob);
                    resolve(url);
                } else {
                    reject(new Error('No audio data'));
                }
            };

            // 发送SSML
            setTimeout(() => {
                const ssml = `<speak version='1.0' xmlns='https://www.w3.org/2001/10/synthesis' xml:lang='zh-CN'>` +
                    `<voice name='${this.voice}'>` +
                    `<prosody rate='-20%' pitch='+5Hz'>${text}</prosody>` +
                    `</voice></speak>`;
                ws.send(ssml);
            }, 500);

            // 超时处理
            setTimeout(() => {
                if (ws.readyState === WebSocket.OPEN) {
                    ws.close();
                    reject(new Error('TTS timeout'));
                }
            }, 10000);
        });
    }
}

// 导出
window.EdgeTTS = EdgeTTS;