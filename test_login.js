// 测试登录功能脚本
const http = require('http');

// 测试后端登录API
function testLoginAPI() {
    return new Promise((resolve, reject) => {
        const postData = JSON.stringify({
            username: 'admin',
            password: 'admin123'
        });
        
        const options = {
            hostname: '127.0.0.1',
            port: 5000,
            path: '/api/admin/login',
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Content-Length': Buffer.byteLength(postData)
            }
        };
        
        const req = http.request(options, (res) => {
            let data = '';
            
            res.on('data', (chunk) => {
                data += chunk;
            });
            
            res.on('end', () => {
                try {
                    const result = JSON.parse(data);
                    console.log('✅ 登录API响应:', JSON.stringify(result, null, 2));
                    
                    if (result.code === 0 && result.data && result.data.token) {
                        console.log('✅ 登录成功，token:', result.data.token.substring(0, 20) + '...');
                        resolve(result);
                    } else {
                        console.error('❌ 登录失败:', result.message);
                        reject(result);
                    }
                } catch (e) {
                    console.error('❌ 解析响应失败:', e);
                    reject(e);
                }
            });
        });
        
        req.on('error', (e) => {
            console.error('❌ 请求失败:', e);
            reject(e);
        });
        
        req.write(postData);
        req.end();
    });
}

// 运行测试
async function runTests() {
    console.log('🧪 开始测试管理员登录功能...\n');
    
    try {
        await testLoginAPI();
        console.log('\n✅ 所有测试通过！');
    } catch (e) {
        console.error('\n❌ 测试失败:', e);
        process.exit(1);
    }
}

runTests();
