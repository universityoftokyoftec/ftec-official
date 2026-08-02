/**
 * 東京大学 F-tec 公式サイト お問い合わせフォーム受信スクリプト
 *
 * 導入時は university.of.tokyo.ftec@gmail.com でデプロイしてください。
 * ウェブアプリ設定:
 *   実行するユーザー: 自分
 *   アクセスできるユーザー: ログインしていない人を含む全員
 */

const CONFIG = Object.freeze({
  destinationEmail: 'university.of.tokyo.ftec@gmail.com',
  senderName: '東京大学 F-tec 公式サイト',
  subjectPrefix: '[F-tec公式サイト]',
  contactPageUrl: 'https://ftec-official.tomokiogawa.chatgpt.site/contact/',
  timeZone: 'Asia/Tokyo',
  autoReply: true,
  duplicateWindowSeconds: 120,
  maxLength: Object.freeze({
    category: 40,
    name: 100,
    organization: 200,
    email: 254,
    phone: 50,
    subject: 100,
    message: 3000,
    sourcePage: 500,
    referrer: 500,
    browserTime: 80,
  }),
});

const ALLOWED_CATEGORIES = Object.freeze([
  '入会案内',
  '協賛・ご支援',
  '取材・メディア',
  '研究・技術連携',
  'OBOGの皆さま',
  'グッズ購入',
  'その他',
]);

function doGet() {
  return renderPage_(
    'F-tec お問い合わせ受付',
    'このURLは、F-tec公式サイトのお問い合わせ送信に使用されています。',
    '',
    false,
  );
}

function doPost(e) {
  let returnUrl = '';
  try {
    const params = (e && e.parameter) || {};
    returnUrl = safeReturnUrl_(params.sourcePage) || CONFIG.contactPageUrl;

    // ハニーポットに入力がある場合は、ボットとみなしてメールを送信しません。
    // 成否の判定材料をボットへ与えないため、通常の完了画面を返します。
    if (clean_(params.website, 200)) {
      return renderPage_(
        '送信が完了しました',
        'お問い合わせを受け付けました。',
        '',
        true,
        returnUrl,
      );
    }

    const data = normalizeAndValidate_(params);
    const referenceId = createReferenceId_();
    const receivedAt = Utilities.formatDate(new Date(), CONFIG.timeZone, 'yyyy-MM-dd HH:mm:ss');
    const duplicateKey = makeDuplicateKey_(data);
    const cache = CacheService.getScriptCache();
    const lock = LockService.getScriptLock();

    if (!lock.tryLock(10000)) {
      throw new Error('ただいま送信が混み合っています。少し時間をおいて再度お試しください。');
    }

    try {
      if (cache.get(duplicateKey)) {
        return renderPage_(
          '送信済みです',
          '同じ内容のお問い合わせは、すでに受け付けています。二重送信の必要はありません。',
          '',
          true,
          returnUrl,
        );
      }

      const requiredRecipients = CONFIG.autoReply ? 2 : 1;
      if (MailApp.getRemainingDailyQuota() < requiredRecipients) {
        throw new Error('本日のメール送信上限に達しました。時間をおいて再度お試しください。');
      }

      sendNotification_(data, referenceId, receivedAt);
      if (CONFIG.autoReply) {
        sendAutoReply_(data, referenceId, receivedAt);
      }

      cache.put(duplicateKey, referenceId, CONFIG.duplicateWindowSeconds);
    } finally {
      lock.releaseLock();
    }

    return renderPage_(
      '送信が完了しました',
      'F-tecへお問い合わせを送信しました。ご入力のメールアドレスにも受付確認メールをお送りしています。',
      '受付番号：' + referenceId,
      true,
      returnUrl,
    );
  } catch (error) {
    console.error(error && error.stack ? error.stack : error);
    return renderPage_(
      '送信できませんでした',
      error && error.message
        ? String(error.message)
        : '通信またはメール送信で問題が発生しました。時間をおいて再度お試しください。',
      '解決しない場合は university.of.tokyo.ftec@gmail.com まで直接ご連絡ください。',
      false,
      returnUrl,
    );
  }
}

function normalizeAndValidate_(params) {
  const data = {
    category: clean_(params.category, CONFIG.maxLength.category),
    name: clean_(params.name, CONFIG.maxLength.name),
    organization: clean_(params.organization, CONFIG.maxLength.organization),
    email: clean_(params.email, CONFIG.maxLength.email).toLowerCase(),
    phone: clean_(params.phone, CONFIG.maxLength.phone),
    subject: clean_(params.subject, CONFIG.maxLength.subject),
    message: cleanMultiline_(params.message, CONFIG.maxLength.message),
    privacyConsent: clean_(params.privacyConsent, 20),
    sourcePage: clean_(params.sourcePage, CONFIG.maxLength.sourcePage),
    referrer: clean_(params.referrer, CONFIG.maxLength.referrer),
    browserTime: clean_(params.browserTime, CONFIG.maxLength.browserTime),
    formVersion: clean_(params.formVersion, 50),
  };

  if (!ALLOWED_CATEGORIES.includes(data.category)) {
    throw new Error('お問い合わせ種別を選択してください。');
  }
  if (!data.name) throw new Error('お名前を入力してください。');
  if (!isValidEmail_(data.email)) throw new Error('メールアドレスを正しく入力してください。');
  if (!data.subject) throw new Error('件名を入力してください。');
  if (!data.message) throw new Error('お問い合わせ内容を入力してください。');
  if (data.privacyConsent !== 'agreed') {
    throw new Error('個人情報の利用目的への同意が必要です。');
  }

  return data;
}

function sendNotification_(data, referenceId, receivedAt) {
  const subject = `${CONFIG.subjectPrefix} [${data.category}] ${data.subject}`;
  const plainBody = [
    'F-tec公式サイトからお問い合わせが届きました。',
    '',
    `受付番号：${referenceId}`,
    `受信日時：${receivedAt}（日本時間）`,
    `お問い合わせ種別：${data.category}`,
    `お名前：${data.name}`,
    `ご所属：${data.organization || '未入力'}`,
    `メールアドレス：${data.email}`,
    `電話番号：${data.phone || '未入力'}`,
    `件名：${data.subject}`,
    '',
    'お問い合わせ内容：',
    data.message,
    '',
    '--- 送信情報 ---',
    `送信元ページ：${data.sourcePage || '不明'}`,
    `参照元：${data.referrer || 'なし'}`,
    `ブラウザ送信時刻：${data.browserTime || '不明'}`,
    `フォーム版：${data.formVersion || '不明'}`,
    '',
    'このメールに返信すると、お問い合わせ者のメールアドレスへ返信できます。',
  ].join('\n');

  const htmlBody = `
    <div style="font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans JP',sans-serif;line-height:1.75;color:#13203b;max-width:720px">
      <h2 style="border-bottom:3px solid #1d4ed8;padding-bottom:10px">F-tec公式サイトからのお問い合わせ</h2>
      <p><strong>受付番号：</strong>${escapeHtml_(referenceId)}<br>
      <strong>受信日時：</strong>${escapeHtml_(receivedAt)}（日本時間）</p>
      <table style="border-collapse:collapse;width:100%">
        ${rowHtml_('お問い合わせ種別', data.category)}
        ${rowHtml_('お名前', data.name)}
        ${rowHtml_('ご所属', data.organization || '未入力')}
        ${rowHtml_('メールアドレス', data.email)}
        ${rowHtml_('電話番号', data.phone || '未入力')}
        ${rowHtml_('件名', data.subject)}
      </table>
      <h3 style="margin-top:26px">お問い合わせ内容</h3>
      <div style="white-space:pre-wrap;background:#f4f7fb;padding:18px;border-radius:8px">${escapeHtml_(data.message)}</div>
      <p style="font-size:12px;color:#667085;margin-top:24px">送信元ページ：${escapeHtml_(data.sourcePage || '不明')}<br>
      参照元：${escapeHtml_(data.referrer || 'なし')}<br>
      ブラウザ送信時刻：${escapeHtml_(data.browserTime || '不明')}<br>
      フォーム版：${escapeHtml_(data.formVersion || '不明')}</p>
      <p><strong>このメールにそのまま返信すると、お問い合わせ者へ返信できます。</strong></p>
    </div>`;

  MailApp.sendEmail({
    to: CONFIG.destinationEmail,
    subject: subject,
    body: plainBody,
    htmlBody: htmlBody,
    name: CONFIG.senderName,
    replyTo: data.email,
  });
}

function sendAutoReply_(data, referenceId, receivedAt) {
  const subject = `【東京大学 F-tec】お問い合わせを受け付けました（${referenceId}）`;
  const plainBody = [
    `${data.name} 様`,
    '',
    '東京大学鳥人間サークルF-tecです。',
    'お問い合わせを受け付けました。内容を確認のうえ、担当者からご返信いたします。',
    '',
    `受付番号：${referenceId}`,
    `受付日時：${receivedAt}（日本時間）`,
    `お問い合わせ種別：${data.category}`,
    `件名：${data.subject}`,
    '',
    'お問い合わせ内容：',
    data.message,
    '',
    '※このメールは自動送信です。追加のご連絡は、このメールへの返信または',
    `${CONFIG.destinationEmail} までお願いいたします。`,
    '',
    '東京大学鳥人間サークル F-tec',
  ].join('\n');

  MailApp.sendEmail({
    to: data.email,
    subject: subject,
    body: plainBody,
    name: CONFIG.senderName,
    replyTo: CONFIG.destinationEmail,
  });
}

function renderPage_(title, message, detail, success, returnUrl) {
  const accent = success ? '#16a34a' : '#1d4ed8';
  const safeUrl = safeReturnUrl_(returnUrl) || CONFIG.contactPageUrl;
  const returnButton = safeUrl
    ? `<a href="${escapeHtml_(safeUrl)}" target="_top" rel="noopener" style="display:inline-block;margin-top:24px;padding:13px 24px;background:#0b1b40;color:#fff;text-decoration:none;border-radius:4px">お問い合わせページへ戻る</a>`
    : '<button type="button" onclick="history.back()" style="margin-top:24px;padding:13px 24px;background:#0b1b40;color:#fff;border:0;border-radius:4px;cursor:pointer">前のページへ戻る</button>';

  return HtmlService.createHtmlOutput(`<!doctype html>
<html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><base target="_top">
<title>${escapeHtml_(title)}</title></head>
<body style="margin:0;background:#f3f5f8;color:#0b1b40;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','Noto Sans JP',sans-serif">
<main style="min-height:100vh;display:grid;place-items:center;padding:24px;box-sizing:border-box">
  <section style="background:#fff;width:min(680px,100%);padding:clamp(30px,7vw,64px);box-sizing:border-box;border-top:6px solid ${accent};box-shadow:0 12px 40px rgba(11,27,64,.12)">
    <p style="font-size:12px;letter-spacing:.18em;color:#2563eb;font-weight:700">TOKYO UNIVERSITY F-TEC</p>
    <h1 style="font-family:serif;font-size:clamp(30px,6vw,48px);font-weight:500;margin:14px 0 22px">${escapeHtml_(title)}</h1>
    <p style="font-size:17px;line-height:1.9;margin:0">${escapeHtml_(message)}</p>
    ${detail ? `<p style="margin-top:18px;padding:14px 16px;background:#f4f7fb;line-height:1.7">${escapeHtml_(detail)}</p>` : ''}
    ${returnButton}
  </section>
</main></body></html>`).setTitle(title);
}

function clean_(value, maxLength) {
  return String(value == null ? '' : value)
    .replace(/\u0000/g, '')
    .replace(/\r\n?/g, '\n')
    .trim()
    .slice(0, maxLength);
}

function cleanMultiline_(value, maxLength) {
  return clean_(value, maxLength).replace(/\n{4,}/g, '\n\n\n');
}

function isValidEmail_(email) {
  if (!email || /[\r\n]/.test(email)) return false;
  return /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email);
}

function safeReturnUrl_(value) {
  const url = clean_(value, 500);
  return /^https?:\/\//i.test(url) ? url : '';
}

function makeDuplicateKey_(data) {
  const raw = [data.email, data.category, data.subject, data.message].join('|');
  const digest = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, raw, Utilities.Charset.UTF_8);
  return 'submission-' + Utilities.base64EncodeWebSafe(digest).slice(0, 40);
}

function createReferenceId_() {
  const date = Utilities.formatDate(new Date(), CONFIG.timeZone, 'yyyyMMdd');
  return `FTEC-${date}-${Utilities.getUuid().replace(/-/g, '').slice(0, 8).toUpperCase()}`;
}

function rowHtml_(label, value) {
  return `<tr><th style="text-align:left;vertical-align:top;padding:10px;border-bottom:1px solid #d9e0ea;width:30%;background:#f7f9fc">${escapeHtml_(label)}</th><td style="padding:10px;border-bottom:1px solid #d9e0ea">${escapeHtml_(value)}</td></tr>`;
}

function escapeHtml_(value) {
  return String(value == null ? '' : value)
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;');
}
