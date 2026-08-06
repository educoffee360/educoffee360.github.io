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
  if (!payload || !payload.sub) return null;

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
  clearToken();
  ["userId", "userName", "userRole", "current_userid", "current_user_name", "current_user_role", "loggedin", "isLoggedIn", "user"].forEach((key) => {
    try {
      localStorage.removeItem(key);
    } catch {
      /* ignore storage failures */
    }
  });

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

    const detail =
      errorPayload.detail ||
      errorPayload.message ||
      errorPayload.error ||
      `Request failed with status ${response.status}`;
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
      },
    });
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function GetUserByID(id = getCurrentUserId()) {
  try {
    return await requestJson(`/user/${requireId(id, "user id")}`);
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

function bindGlobals() {
  Object.assign(globalThis, {
    api_url,
    TOKEN_KEY,
    saveToken,
    getToken,
    clearToken,
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
    GetUserByID,
    Login,
    CreateNewBatch,
    UpdateBatch,
    DeleteBatch,
    GetBatchesByTID,
    GetBatchesByTeacherId,
    GetMyStudents,
    GetStudentsByBC,
    GetStudentsInBatch,
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
    GetAllUsers,
    GetAllBatches,
    GetAllResults,
    GetAllNotices,
  });
}

bindGlobals();
