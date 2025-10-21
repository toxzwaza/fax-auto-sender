# Laravel/Inertia/Vue.js アプリケーションからのFAX送信

## 📋 概要

Laravel/Inertia/Vue.jsアプリケーションからFAX自動送信システムにデータを送信し、管理画面で送信履歴とステータスを確認できます。

## 🔧 API仕様

### FAX送信API

**エンドポイント**: `POST /api/send_fax`

**認証**: `X-API-Key` ヘッダーが必要

**リクエスト例**:
```json
{
    "fax_number": "03-1234-5678",
    "pdf_url": "https://example.com/document.pdf",
    "user_id": 123,
    "document_id": 456,
    "company_id": 789,
    "priority": "high",
    "callback_url": "https://your-app.com/fax/callback",
    "metadata": {
        "department": "営業部",
        "client_name": "株式会社サンプル"
    }
}
```

**レスポンス例**:
```json
{
    "success": true,
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "message": "FAX送信を開始しました",
    "status": "pending"
}
```

### ジョブステータス取得API

**エンドポイント**: `GET /api/job_status/{job_id}`

**レスポンス例**:
```json
{
    "id": 1,
    "job_id": "550e8400-e29b-41d4-a716-446655440000",
    "fax_number": "03-1234-5678",
    "pdf_url": "https://example.com/document.pdf",
    "status": "completed",
    "message": "FAX送信完了",
    "created_at": "2024-01-15T10:30:00",
    "updated_at": "2024-01-15T10:35:00",
    "completed_at": "2024-01-15T10:35:00",
    "error_message": null,
    "laravel_data": "{\"user_id\":123,\"document_id\":456}",
    "retry_count": 0
}
```

## 🚀 Laravel実装例

### 1. Service Providerの作成

```php
// app/Services/FaxService.php
<?php

namespace App\Services;

use Illuminate\Support\Facades\Http;
use Illuminate\Support\Facades\Log;

class FaxService
{
    private string $apiUrl;
    private string $apiKey;

    public function __construct()
    {
        $this->apiUrl = config('fax.api_url', 'http://localhost:5000');
        $this->apiKey = config('fax.api_key', 'default_secret_key_change_in_production');
    }

    public function sendFax(array $data): array
    {
        try {
            $response = Http::withHeaders([
                'X-API-Key' => $this->apiKey,
                'Content-Type' => 'application/json',
            ])->post($this->apiUrl . '/api/send_fax', $data);

            if ($response->successful()) {
                return $response->json();
            }

            throw new \Exception('FAX送信API エラー: ' . $response->body());
        } catch (\Exception $e) {
            Log::error('FAX送信エラー', [
                'error' => $e->getMessage(),
                'data' => $data
            ]);
            throw $e;
        }
    }

    public function getJobStatus(string $jobId): array
    {
        try {
            $response = Http::get($this->apiUrl . '/api/job_status/' . $jobId);

            if ($response->successful()) {
                return $response->json();
            }

            throw new \Exception('ステータス取得API エラー: ' . $response->body());
        } catch (\Exception $e) {
            Log::error('FAXステータス取得エラー', [
                'error' => $e->getMessage(),
                'job_id' => $jobId
            ]);
            throw $e;
        }
    }
}
```

### 2. Controllerの実装

```php
// app/Http/Controllers/FaxController.php
<?php

namespace App\Http\Controllers;

use App\Services\FaxService;
use Illuminate\Http\Request;
use Illuminate\Http\JsonResponse;

class FaxController extends Controller
{
    private FaxService $faxService;

    public function __construct(FaxService $faxService)
    {
        $this->faxService = $faxService;
    }

    public function send(Request $request): JsonResponse
    {
        $request->validate([
            'fax_number' => 'required|string',
            'pdf_url' => 'required|url',
            'document_id' => 'nullable|integer',
            'priority' => 'nullable|in:low,normal,high',
        ]);

        try {
            $data = [
                'fax_number' => $request->fax_number,
                'pdf_url' => $request->pdf_url,
                'user_id' => auth()->id(),
                'document_id' => $request->document_id,
                'company_id' => auth()->user()->company_id ?? null,
                'priority' => $request->priority ?? 'normal',
                'callback_url' => route('fax.callback'),
                'metadata' => [
                    'user_name' => auth()->user()->name,
                    'department' => auth()->user()->department ?? null,
                ]
            ];

            $result = $this->faxService->sendFax($data);

            return response()->json([
                'success' => true,
                'job_id' => $result['job_id'],
                'message' => 'FAX送信を開始しました'
            ]);

        } catch (\Exception $e) {
            return response()->json([
                'success' => false,
                'error' => $e->getMessage()
            ], 500);
        }
    }

    public function status(string $jobId): JsonResponse
    {
        try {
            $status = $this->faxService->getJobStatus($jobId);
            return response()->json($status);
        } catch (\Exception $e) {
            return response()->json([
                'error' => $e->getMessage()
            ], 500);
        }
    }

    public function callback(Request $request): JsonResponse
    {
        // FAX送信完了時のコールバック処理
        $jobId = $request->input('job_id');
        $status = $request->input('status');
        
        // データベースの更新処理など
        // ...

        return response()->json(['success' => true]);
    }
}
```

### 3. Vue.jsコンポーネント

```vue
<!-- resources/js/Pages/Fax/Send.vue -->
<template>
    <div class="fax-send">
        <h1>FAX送信</h1>
        
        <form @submit.prevent="sendFax">
            <div class="form-group">
                <label>FAX番号</label>
                <input 
                    v-model="form.fax_number" 
                    type="tel" 
                    required 
                    placeholder="03-1234-5678"
                />
            </div>
            
            <div class="form-group">
                <label>PDFファイルURL</label>
                <input 
                    v-model="form.pdf_url" 
                    type="url" 
                    required 
                    placeholder="https://example.com/document.pdf"
                />
            </div>
            
            <div class="form-group">
                <label>優先度</label>
                <select v-model="form.priority">
                    <option value="low">低</option>
                    <option value="normal">通常</option>
                    <option value="high">高</option>
                </select>
            </div>
            
            <button type="submit" :disabled="loading">
                {{ loading ? '送信中...' : 'FAX送信' }}
            </button>
        </form>
        
        <div v-if="result" class="result">
            <h3>送信結果</h3>
            <p>ジョブID: {{ result.job_id }}</p>
            <p>ステータス: {{ result.status }}</p>
        </div>
    </div>
</template>

<script>
import { ref } from 'vue'
import { router } from '@inertiajs/vue3'

export default {
    setup() {
        const form = ref({
            fax_number: '',
            pdf_url: '',
            priority: 'normal'
        })
        
        const loading = ref(false)
        const result = ref(null)
        
        const sendFax = async () => {
            loading.value = true
            
            try {
                const response = await fetch('/fax/send', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRF-TOKEN': document.querySelector('meta[name="csrf-token"]').content
                    },
                    body: JSON.stringify(form.value)
                })
                
                const data = await response.json()
                
                if (data.success) {
                    result.value = data
                    // ステータス監視を開始
                    monitorStatus(data.job_id)
                } else {
                    alert('送信エラー: ' + data.error)
                }
            } catch (error) {
                alert('送信エラー: ' + error.message)
            } finally {
                loading.value = false
            }
        }
        
        const monitorStatus = async (jobId) => {
            const interval = setInterval(async () => {
                try {
                    const response = await fetch(`/fax/status/${jobId}`)
                    const status = await response.json()
                    
                    result.value.status = status.status
                    
                    if (status.status === 'completed' || status.status === 'error') {
                        clearInterval(interval)
                    }
                } catch (error) {
                    console.error('ステータス取得エラー:', error)
                }
            }, 2000)
        }
        
        return {
            form,
            loading,
            result,
            sendFax
        }
    }
}
</script>
```

### 4. ルート設定

```php
// routes/web.php
Route::middleware(['auth'])->group(function () {
    Route::post('/fax/send', [FaxController::class, 'send']);
    Route::get('/fax/status/{jobId}', [FaxController::class, 'status']);
    Route::post('/fax/callback', [FaxController::class, 'callback']);
});
```

### 5. 設定ファイル

```php
// config/fax.php
<?php

return [
    'api_url' => env('FAX_API_URL', 'http://localhost:5000'),
    'api_key' => env('FAX_API_KEY', 'default_secret_key_change_in_production'),
];
```

```env
# .env
FAX_API_URL=http://localhost:5000
FAX_API_KEY=your_secure_api_key_here
```

## 📊 管理画面

管理画面（`http://localhost:5000/admin`）では以下が確認できます：

- **統計情報**: 総送信数、今日の送信数、今月の送信数、エラー数
- **送信履歴**: 全送信履歴の一覧表示
- **ステータス管理**: 各ジョブの詳細ステータスと履歴
- **再試行機能**: エラーになったジョブの再実行
- **フィルター機能**: ステータス別、日付別での絞り込み

## 🔒 セキュリティ

- API認証には`X-API-Key`ヘッダーを使用
- 本番環境では強力なAPIキーを設定
- CORS設定でアクセス元を制限可能
- ログ機能で全ての送信履歴を記録

## 📝 注意事項

1. **APIキーの管理**: 本番環境では必ず強力なAPIキーを設定
2. **エラーハンドリング**: ネットワークエラーやタイムアウトを適切に処理
3. **リトライ機能**: 一時的なエラーに対する再試行機能を実装
4. **ログ管理**: 送信履歴とエラーログを適切に管理
