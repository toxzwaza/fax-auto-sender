<?php

namespace App\Models;

use Illuminate\Database\Eloquent\Factories\HasFactory;
use Illuminate\Database\Eloquent\Model;
use Illuminate\Support\Carbon;

/**
 * FAX送信パラメータモデル
 *
 * @property string $id UUID
 * @property string|null $file_url ファイルURL
 * @property string|null $fax_number FAX番号
 * @property int $status ステータス（0:待機中, 1:完了, 2:処理中, -1:エラー）
 * @property string|null $error_message エラーメッセージ
 * @property string|null $converted_pdf_path 変換後PDFファイルパス
 * @property string|null $request_user 依頼者名
 * @property string|null $file_name ファイル名
 * @property string|null $callback_url コールバックURL
 * @property string|null $order_destination 発注先
 * @property Carbon $created_at 作成日時
 * @property Carbon $updated_at 更新日時
 */
class FaxParameter extends Model
{
    use HasFactory;

    /**
     * テーブル名
     *
     * @var string
     */
    protected $table = 'fax_parameters';

    /**
     * 主キーのインクリメント設定
     * UUIDを使用するためfalse
     *
     * @var bool
     */
    public $incrementing = false;

    /**
     * 主キーのデータ型
     *
     * @var string
     */
    protected $keyType = 'string';

    /**
     * 代入可能な属性
     *
     * @var array<int, string>
     */
    protected $fillable = [
        'id',
        'file_url',
        'fax_number',
        'status',
        'error_message',
        'converted_pdf_path',
        'request_user',
        'file_name',
        'callback_url',
        'order_destination',
    ];

    /**
     * キャストする属性
     *
     * @var array<string, string>
     */
    protected $casts = [
        'status' => 'integer',
        'created_at' => 'datetime',
        'updated_at' => 'datetime',
    ];

    /**
     * ステータス定数
     */
    const STATUS_PENDING = 0;     // 待機中
    const STATUS_COMPLETED = 1;   // 完了
    const STATUS_PROCESSING = 2;  // 処理中
    const STATUS_ERROR = -1;      // エラー

    /**
     * ステータスラベル
     *
     * @var array<int, string>
     */
    public static $statusLabels = [
        self::STATUS_PENDING => '待機中',
        self::STATUS_COMPLETED => '完了',
        self::STATUS_PROCESSING => '処理中',
        self::STATUS_ERROR => 'エラー',
    ];

    /**
     * ステータスラベルのアクセサ
     *
     * @return string
     */
    public function getStatusLabelAttribute(): string
    {
        return self::$statusLabels[$this->status] ?? '不明';
    }

    /**
     * ステータスクラス（CSS用）のアクセサ
     *
     * @return string
     */
    public function getStatusClassAttribute(): string
    {
        return match ($this->status) {
            self::STATUS_PENDING => 'status-pending',
            self::STATUS_COMPLETED => 'status-completed',
            self::STATUS_PROCESSING => 'status-processing',
            self::STATUS_ERROR => 'status-error',
            default => 'status-unknown',
        };
    }

    /**
     * 待機中のリクエストを取得するスコープ
     *
     * @param \Illuminate\Database\Eloquent\Builder $query
     * @return \Illuminate\Database\Eloquent\Builder
     */
    public function scopePending($query)
    {
        return $query->where('status', self::STATUS_PENDING);
    }

    /**
     * 完了したリクエストを取得するスコープ
     *
     * @param \Illuminate\Database\Eloquent\Builder $query
     * @return \Illuminate\Database\Eloquent\Builder
     */
    public function scopeCompleted($query)
    {
        return $query->where('status', self::STATUS_COMPLETED);
    }

    /**
     * 処理中のリクエストを取得するスコープ
     *
     * @param \Illuminate\Database\Eloquent\Builder $query
     * @return \Illuminate\Database\Eloquent\Builder
     */
    public function scopeProcessing($query)
    {
        return $query->where('status', self::STATUS_PROCESSING);
    }

    /**
     * エラーのリクエストを取得するスコープ
     *
     * @param \Illuminate\Database\Eloquent\Builder $query
     * @return \Illuminate\Database\Eloquent\Builder
     */
    public function scopeError($query)
    {
        return $query->where('status', self::STATUS_ERROR);
    }

    /**
     * 作成日時でソートするスコープ
     *
     * @param \Illuminate\Database\Eloquent\Builder $query
     * @param string $direction
     * @return \Illuminate\Database\Eloquent\Builder
     */
    public function scopeOrderByCreated($query, $direction = 'desc')
    {
        return $query->orderBy('created_at', $direction);
    }

    /**
     * FAX番号で検索するスコープ
     *
     * @param \Illuminate\Database\Eloquent\Builder $query
     * @param string $faxNumber
     * @return \Illuminate\Database\Eloquent\Builder
     */
    public function scopeWhereFaxNumber($query, $faxNumber)
    {
        return $query->where('fax_number', 'like', "%{$faxNumber}%");
    }

    /**
     * 依頼者で検索するスコープ
     *
     * @param \Illuminate\Database\Eloquent\Builder $query
     * @param string $requestUser
     * @return \Illuminate\Database\Eloquent\Builder
     */
    public function scopeWhereRequestUser($query, $requestUser)
    {
        return $query->where('request_user', 'like', "%{$requestUser}%");
    }

    /**
     * ファイル名で検索するスコープ
     *
     * @param \Illuminate\Database\Eloquent\Builder $query
     * @param string $fileName
     * @return \Illuminate\Database\Eloquent\Builder
     */
    public function scopeWhereFileName($query, $fileName)
    {
        return $query->where('file_name', 'like', "%{$fileName}%");
    }

    /**
     * 発注先で検索するスコープ
     *
     * @param \Illuminate\Database\Eloquent\Builder $query
     * @param string $orderDestination
     * @return \Illuminate\Database\Eloquent\Builder
     */
    public function scopeWhereOrderDestination($query, $orderDestination)
    {
        return $query->where('order_destination', 'like', "%{$orderDestination}%");
    }

    /**
     * 複数の条件で検索するスコープ
     *
     * @param \Illuminate\Database\Eloquent\Builder $query
     * @param array $filters
     * @return \Illuminate\Database\Eloquent\Builder
     */
    public function scopeSearch($query, array $filters = [])
    {
        if (!empty($filters['status']) || $filters['status'] === '0' || $filters['status'] === 0) {
            $query->where('status', $filters['status']);
        }

        if (!empty($filters['fax_number'])) {
            $query->whereFaxNumber($filters['fax_number']);
        }

        if (!empty($filters['request_user'])) {
            $query->whereRequestUser($filters['request_user']);
        }

        if (!empty($filters['file_name'])) {
            $query->whereFileName($filters['file_name']);
        }

        if (!empty($filters['order_destination'])) {
            $query->whereOrderDestination($filters['order_destination']);
        }

        if (!empty($filters['date_from'])) {
            $query->where('created_at', '>=', $filters['date_from']);
        }

        if (!empty($filters['date_to'])) {
            $query->where('created_at', '<=', $filters['date_to']);
        }

        return $query;
    }

    /**
     * ステータスが待機中かどうかを判定
     *
     * @return bool
     */
    public function isPending(): bool
    {
        return $this->status === self::STATUS_PENDING;
    }

    /**
     * ステータスが完了かどうかを判定
     *
     * @return bool
     */
    public function isCompleted(): bool
    {
        return $this->status === self::STATUS_COMPLETED;
    }

    /**
     * ステータスが処理中かどうかを判定
     *
     * @return bool
     */
    public function isProcessing(): bool
    {
        return $this->status === self::STATUS_PROCESSING;
    }

    /**
     * ステータスがエラーかどうかを判定
     *
     * @return bool
     */
    public function isError(): bool
    {
        return $this->status === self::STATUS_ERROR;
    }

    /**
     * ステータスを待機中に変更
     *
     * @return bool
     */
    public function markAsPending(): bool
    {
        return $this->update(['status' => self::STATUS_PENDING]);
    }

    /**
     * ステータスを処理中に変更
     *
     * @return bool
     */
    public function markAsProcessing(): bool
    {
        return $this->update(['status' => self::STATUS_PROCESSING]);
    }

    /**
     * ステータスを完了に変更
     *
     * @return bool
     */
    public function markAsCompleted(): bool
    {
        return $this->update(['status' => self::STATUS_COMPLETED]);
    }

    /**
     * ステータスをエラーに変更
     *
     * @param string|null $errorMessage
     * @return bool
     */
    public function markAsError(?string $errorMessage = null): bool
    {
        $data = ['status' => self::STATUS_ERROR];
        if ($errorMessage) {
            $data['error_message'] = $errorMessage;
        }
        return $this->update($data);
    }

    /**
     * 作成日時をフォーマットしたアクセサ
     *
     * @return string
     */
    public function getFormattedCreatedAtAttribute(): string
    {
        return $this->created_at ? $this->created_at->format('Y年m月d日 H:i:s') : '';
    }

    /**
     * 更新日時をフォーマットしたアクセサ
     *
     * @return string
     */
    public function getFormattedUpdatedAtAttribute(): string
    {
        return $this->updated_at ? $this->updated_at->format('Y年m月d日 H:i:s') : '';
    }

    /**
     * 処理時間を計算したアクセサ（分単位）
     *
     * @return float|null
     */
    public function getProcessingTimeAttribute(): ?float
    {
        if ($this->created_at && $this->updated_at) {
            return $this->created_at->diffInMinutes($this->updated_at);
        }
        return null;
    }
}
