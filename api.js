const api_url = (typeof window !== "undefined" && window.API_URL) ||
  (typeof globalThis !== "undefined" && globalThis.API_URL) ||
  "https://educoffee.onrender.com/api";
// const api_url = "http://127.0.0.1:8000/api";

const TOKEN_KEY = "educoffee_token";
const DEFAULT_AUTH_REDIRECT = "auth.html";

function saveToken(token) {
  localStorage.setItem(TOKEN_KEY, token);
}

function getToken() {
  return localStorage.getItem(TOKEN_KEY);
}

function clearToken() {
  localStorage.removeItem(TOKEN_KEY);
}

function clearAuthState() {
  clearToken();
  ["userId", "userName", "userRole", "userEmail", "current_userid", "current_user_id", "current_user_name", "current_user_role", "current_user_email", "loggedin", "isLoggedIn", "user", "access_token", "token"].forEach((key) => {
    try {
      localStorage.removeItem(key);
      sessionStorage.removeItem(key);
    } catch {
      /* ignore storage failures */
    }
  });
}

function isLoggedIn() {
  return !!getToken();
}

function decodeJwtPayload(token) {
  try {
    const payload = token.split(".")[1];
    if (!payload) return null;

    let base64 = payload.replace(/-/g, "+").replace(/_/g, "/");
    while (base64.length % 4) base64 += "=";

    const json = atob(base64);
    return JSON.parse(json);
  } catch {
    return null;
  }
}

function getCurrentSession() {
  const token = getToken();
  if (!token) return null;

  const payload = decodeJwtPayload(token);
  if (!payload || !payload.sub) {
    clearAuthState();
    return null;
  }

  if (payload.exp && payload.exp * 1000 <= Date.now()) {
    clearAuthState();
    return null;
  }

  return {
    id: payload.sub,
    role: payload.role || null,
    name: payload.name || null,
    token,
  };
}

function getCurrentUserId() {
  return getCurrentSession()?.id || null;
}

function getCurrentUserRole() {
  return getCurrentSession()?.role || null;
}

function getCurrentUserName() {
  return getCurrentSession()?.name || null;
}

function logout(redirectUrl = DEFAULT_AUTH_REDIRECT) {
  clearAuthState();

  if (typeof window !== "undefined" && redirectUrl) {
    window.location.href = redirectUrl;
  }
}

function requireSession(options = {}) {
  const { role = null, redirectTo = DEFAULT_AUTH_REDIRECT } = options;
  const session = getCurrentSession();

  if (!session) {
    if (typeof window !== "undefined" && redirectTo) {
      window.location.href = redirectTo;
    }
    return null;
  }

  if (role && session.role !== role) {
    if (typeof window !== "undefined" && redirectTo) {
      window.location.href = redirectTo;
    }
    return null;
  }

  return session;
}

const defaultHeaders = {
  Accept: "application/json",
};

async function requestJson(path, options = {}) {
  const { method = "GET", body, headers = {} } = options;
  const token = getToken();

  const finalHeaders = {
    ...defaultHeaders,
    ...(body !== undefined ? { "Content-Type": "application/json" } : {}),
    ...(token ? { Authorization: `Bearer ${token}` } : {}),
    ...headers,
  };

  const response = await fetch(`${api_url}${path}`, {
    method,
    headers: finalHeaders,
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (!response.ok) {
    let errorPayload = {};
    try {
      errorPayload = await response.json();
    } catch {
      errorPayload = {};
    }

    const rawDetail =
      errorPayload.detail ||
      errorPayload.message ||
      errorPayload.error ||
      `Request failed with status ${response.status}`;
    const detail = Array.isArray(rawDetail)
      ? rawDetail.map((item) => item?.msg || String(item)).join("; ")
      : String(rawDetail);

    if (response.status === 401) {
      clearAuthState();
      if (typeof window !== "undefined" && !window.location.pathname.endsWith("/auth.html")) {
        window.location.replace(DEFAULT_AUTH_REDIRECT);
      }
    }
    if (response.status === 403 && detail.toLowerCase().includes("suspended")) {
      clearAuthState();
      if (typeof window !== "undefined" && !window.location.pathname.endsWith("/auth.html")) {
        window.location.replace(`${DEFAULT_AUTH_REDIRECT}?suspended=1`);
      }
    }
    throw new Error(detail);
  }

  if (response.status === 204) {
    return true;
  }

  try {
    return await response.json();
  } catch {
    return true;
  }
}

async function fetchOrNull(path, options = {}) {
  try {
    return await requestJson(path, options);
  } catch {
    return null;
  }
}

function requireId(value, label, fallback = getCurrentUserId()) {
  const resolved = value ?? fallback;
  if (!resolved) {
    throw new Error(`Missing ${label}`);
  }
  return resolved;
}

async function Register(data) {
  try {
    return await requestJson("/register", {
      method: "POST",
      body: {
        name: data.name,
        email: data.email,
        password: data.password,
        phone: data.phone,
        center_name: data.center_name,
        role: data.role,
        batch_codes: data.batch_codes,
        plan: data.plan,
        location: data.location,
        grade: data.grade,
        verification_token: data.verification_token,
      },
    });
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function SendRegistrationOTP(email) {
  return requestJson("/send_otp", {
    method: "POST",
    body: { email, purpose: "register" },
  });
}

async function VerifyRegistrationOTP(email, code) {
  return requestJson("/verify_otp", {
    method: "POST",
    body: { email, code, purpose: "register" },
  });
}

async function ValidateRegistrationBatch(batchCode) {
  const code = requireId(String(batchCode || "").trim().toUpperCase(), "batch code", null);
  return requestJson(`/batch/validate/${encodeURIComponent(code)}`);
}

async function SendPasswordResetOTP(email) {
  return requestJson("/send_otp", {
    method: "POST",
    body: { email, purpose: "password_reset" },
  });
}

async function VerifyPasswordResetOTP(email, code) {
  return requestJson("/verify_otp", {
    method: "POST",
    body: { email, code, purpose: "password_reset" },
  });
}

async function ResetPassword(resetToken, newPassword) {
  return requestJson("/password/reset", {
    method: "POST",
    body: { reset_token: resetToken, new_password: newPassword },
  });
}

async function ChangePassword(currentPassword, newPassword) {
  return requestJson("/password/change", {
    method: "POST",
    body: { current_password: currentPassword, new_password: newPassword },
  });
}

async function GetUserByID(id = getCurrentUserId()) {
  try {
    return await requestJson(`/user/${requireId(id, "user id")}`);
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function UpdateUserProfile(id = getCurrentUserId(), profile = {}) {
  try {
    return await requestJson(`/user/${requireId(id, "user id")}/profile`, {
      method: "PUT",
      body: {
        name: profile.name,
        phone: profile.phone,
        center_name: profile.center_name ?? null,
      },
    });
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function Login(email, pass) {
  try {
    return await requestJson("/login", {
      method: "POST",
      body: {
        email,
        password: pass,
      },
    });
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function CreateNewBatch(batch = {}) {
  try {
    const teacher_id = requireId(batch.teacher_id, "teacher id");

    return await requestJson("/new_batch/", {
      method: "POST",
      body: {
        name: batch.name,
        year: batch.year,
        schedule: batch.schedule,
        teacher_id,
        code: batch.code,

        // Payment configuration
        fee_amount: batch.fee_amount,
        payment_cycle: batch.payment_cycle,
        custom_period_start: batch.custom_period_start ?? null,
        custom_period_end: batch.custom_period_end ?? null,
      },
    });
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function UpdateBatch(code, batch) {
  try {
    return await requestJson(`/batch/${code}`, {
      method: "PUT",
      body: {
        name: batch.name,
        year: batch.year,
        schedule: batch.schedule,

        // Payment configuration
        fee_amount: batch.fee_amount,
        payment_cycle: batch.payment_cycle,
        custom_period_start: batch.custom_period_start ?? null,
        custom_period_end: batch.custom_period_end ?? null,
      },
    });
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function DeleteBatch(code) {
  try {
    return await requestJson(`/batch/${code}`, {
      method: "DELETE",
    });
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function GetBatchesByTID(teacher_id = getCurrentUserId()) {
  try {
    return await requestJson(`/batches/${requireId(teacher_id, "teacher id")}`);
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function GetBatchesByTeacherId(teacher_id = getCurrentUserId()) {
  return GetBatchesByTID(teacher_id);
}

async function GetMyStudents(teacher_id = getCurrentUserId()) {
  try {
    return await requestJson(`/my_students/${requireId(teacher_id, "teacher id")}`);
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function RemoveMyStudent(student_id) {
  try {
    return await requestJson(`/my_students/${requireId(student_id, "student id", null)}`, {
      method: "DELETE",
    });
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function GetStudentsByBC(batch_code) {
  try {
    return await requestJson(`/students_in_batch/${requireId(batch_code, "batch code")}`);
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function GetStudentsInBatch(batch_code) {
  return GetStudentsByBC(batch_code);
}

async function EnrollInBatch(batch_code) {
  try {
    return await requestJson(`/enroll/${requireId(batch_code, "batch code", null)}`, {
      method: "PUT",
    });
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function GetTeacherPayments(teacher_id = getCurrentUserId()) {
  try {
    return await requestJson(
      `/payments/teacher/${requireId(teacher_id, "teacher id")}`
    );
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function UpdatePayment(student_id, batch_code, status) {
  try {
    return await requestJson(
      `/payment/${requireId(student_id, "student id")}/${requireId(batch_code, "batch code")}`,
      {
        method: "PUT",
        body: {
          status,
        },
      }
    );
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function CreateResult(result = {}) {
  try {
    return await requestJson("/new_result", {
      method: "POST",
      body: {
        title: result.title,
        description: result.description,
        total_marks: result.total_marks,
        batch_code: result.batch_code,
        scores: result.scores,
      },
    });
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function GetStudentResults(student_id = getCurrentUserId()) {
  try {
    return await requestJson(`/results/student/${requireId(student_id, "student id")}`);
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function GetStudentResult(student_id = getCurrentUserId(), result_id) {
  try {
    return await requestJson(`/results/student/${requireId(student_id, "student id")}/${requireId(result_id, "result id", null)}`);
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function GetResultsByBatch(batch_code) {
  return requestJson(`/results/batch/${requireId(batch_code, "batch code")}`);
}

async function DeleteResult(result_id) {
  return requestJson(`/result/${requireId(result_id, "result id", null)}`, { method: "DELETE" });
}

async function GetMyNotices(teacher_id = getCurrentUserId()) {
  try {
    return await requestJson(`/my_notices/${requireId(teacher_id, "teacher id")}`);
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function CreateNotice(notice = {}) {
  try {
    const teacher_id = requireId(notice.teacher_id, "teacher id");
    return await requestJson("/new_notice", {
      method: "POST",
      body: {
        text: notice.text,
        teacher_id,
        batch_codes: notice.batch_codes,
      },
    });
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function CreateNewNotice(notice = {}) {
  return CreateNotice(notice);
}

async function UpdateNotice(noticeId, notice = {}) {
  try {
    const teacher_id = requireId(notice.teacher_id, "teacher id");
    return await requestJson(`/notice/${requireId(noticeId, "notice id")}`, {
      method: "PUT",
      body: {
        text: notice.text,
        teacher_id,
        batch_codes: notice.batch_codes,
      },
    });
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function DeleteNotice(noticeId) {
  try {
    return await requestJson(`/notice/${requireId(noticeId, "notice id")}`, {
      method: "DELETE",
    });
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function GetNoticesForStudent(student_id = getCurrentUserId()) {
  try {
    return await requestJson(`/notices/${requireId(student_id, "student id")}`);
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function SendParentMessage(message = {}) {
  return requestJson("/messages", {
    method: "POST",
    body: {
      student_id: requireId(message.student_id, "student id", null),
      subject: message.subject,
      body: message.body,
    },
  });
}

async function BroadcastParentMessage(message = {}) {
  return requestJson("/messages/broadcast", {
    method: "POST",
    body: {
      batch_codes: Array.isArray(message.batch_codes) ? message.batch_codes : [],
      subject: message.subject,
      body: message.body,
    },
  });
}

async function GetParentMessages(student_id = getCurrentUserId()) {
  return requestJson(`/messages/student/${requireId(student_id, "student id")}`);
}

async function GetAllUsers() {
  return requestJson("/users");
}

async function GetAllBatches() {
  return requestJson("/batches");
}

async function GetAllResults() {
  return requestJson("/results");
}

async function GetAllNotices() {
  return requestJson("/notices");
}

async function GetBillingConfig() {
  return requestJson("/billing/config");
}

async function CreateUpgradeRequest(request = {}) {
  return requestJson("/upgrade-requests", {
    method: "POST",
    body: {
      requested_plan: request.requested_plan,
      method: request.method || "nagad",
      trx_id: request.trx_id || null,
      payment_phone: request.payment_phone || null,
    },
  });
}

async function GetMyUpgradeRequests() {
  return requestJson("/upgrade-requests/mine");
}

async function GetStaffUsers() { return requestJson("/staff/users"); }
async function GetStaffAnalytics() { return requestJson("/staff/analytics"); }
async function GetStaffUpgradeRequests() { return requestJson("/staff/upgrade-requests"); }
async function DecideUpgradeRequest(id, approved, note = "") {
  return requestJson(`/staff/upgrade-requests/${requireId(id, "upgrade request", null)}/decision`, { method: "POST", body: { approved, note } });
}
async function SetTeacherPlan(id, plan) {
  return requestJson(`/staff/teachers/${requireId(id, "teacher id", null)}/plan`, { method: "PUT", body: { plan } });
}
async function BanTeacher(id, reason) {
  return requestJson(`/staff/teachers/${requireId(id, "teacher id", null)}/ban`, { method: "POST", body: { reason } });
}
async function UnbanTeacher(id) {
  return requestJson(`/staff/teachers/${requireId(id, "teacher id", null)}/ban`, { method: "DELETE" });
}
async function RequestTeacherBan(id, reason) {
  return requestJson(`/staff/teachers/${requireId(id, "teacher id", null)}/ban-requests`, { method: "POST", body: { reason } });
}
async function GetBanRequests() { return requestJson("/staff/ban-requests"); }
async function DecideBanRequest(id, approved, note = "") {
  return requestJson(`/staff/ban-requests/${requireId(id, "ban request", null)}/decision`, { method: "POST", body: { approved, note } });
}
async function SendStaffEmail(recipientIds, subject, body) {
  return requestJson("/staff/email", { method: "POST", body: { recipient_ids: recipientIds, subject, body } });
}
async function CreateModerator(data) {
  return requestJson("/staff/moderators", { method: "POST", body: data });
}

function bindGlobals() {
  Object.assign(globalThis, {
    api_url,
    TOKEN_KEY,
    saveToken,
    getToken,
    clearToken,
    clearAuthState,
    isLoggedIn,
    decodeJwtPayload,
    getCurrentSession,
    getCurrentUserId,
    getCurrentUserRole,
    getCurrentUserName,
    logout,
    requireSession,
    requestJson,
    fetchOrNull,
    Register,
    SendRegistrationOTP,
    VerifyRegistrationOTP,
    ValidateRegistrationBatch,
    SendPasswordResetOTP,
    VerifyPasswordResetOTP,
    ResetPassword,
    ChangePassword,
    GetUserByID,
    UpdateUserProfile,
    Login,
    CreateNewBatch,
    UpdateBatch,
    DeleteBatch,
    GetBatchesByTID,
    GetBatchesByTeacherId,
    GetMyStudents,
    RemoveMyStudent,
    GetStudentsByBC,
    GetStudentsInBatch,
    EnrollInBatch,
    GetTeacherPayments,
    UpdatePayment,
    CreateResult,
    GetStudentResults,
    GetStudentResult,
    GetResultsByBatch,
    DeleteResult,
    GetMyNotices,
    CreateNotice,
    CreateNewNotice,
    UpdateNotice,
    DeleteNotice,
    GetNoticesForStudent,
    SendParentMessage,
    BroadcastParentMessage,
    GetParentMessages,
    GetAllUsers,
    GetAllBatches,
    GetAllResults,
    GetAllNotices,
    GetBillingConfig,
    CreateUpgradeRequest,
    GetMyUpgradeRequests,
    GetStaffUsers,
    GetStaffAnalytics,
    GetStaffUpgradeRequests,
    DecideUpgradeRequest,
    SetTeacherPlan,
    BanTeacher,
    UnbanTeacher,
    RequestTeacherBan,
    GetBanRequests,
    DecideBanRequest,
    SendStaffEmail,
    CreateModerator,
  });
}

bindGlobals();
