const api_url = (typeof window !== "undefined" && window.API_URL) || (typeof globalThis !== "undefined" && globalThis.API_URL) || "https://educoffee.onrender.com/api";
// const api_url = "http://127.0.0.1:8000/api";

const defaultHeaders = {
  "Content-Type": "application/json",
  Accept: "application/json",
};

async function requestJson(path, options = {}) {
  const { method = "GET", body, headers = {} } = options;
  const response = await fetch(`${api_url}${path}`, {
    method,
    headers: {
      ...defaultHeaders,
      ...headers,
    },
    body: body === undefined ? undefined : JSON.stringify(body),
  });

  if (!response.ok) {
    let errorPayload = {};

    try {
      errorPayload = await response.json();
    } catch {
      errorPayload = {};
    }

    const detail = errorPayload.detail || errorPayload.message || errorPayload.error || `Request failed with status ${response.status}`;
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

async function GetUserByID(id) {
  try {
    return await requestJson(`/user/${id}`);
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

async function CreateNewBatch(batch) {
  try {
    return await requestJson("/new_batch", {
      method: "POST",
      body: {
        name: batch.name,
        year: batch.year,
        schedule: batch.schedule,
        teacher_id: batch.teacher_id,
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

async function GetBatchesByTID(teacher_id) {
  try {
    return await requestJson(`/batches/${teacher_id}`);
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function GetMyStudents(teacher_id) {
  try {
    return await requestJson(`/my_students/${teacher_id}`);
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function GetStudentsByBC(batch_code) {
  try {
    return await requestJson(`/students_in_batch/${batch_code}`);
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function CreateResult(result) {
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

async function GetStudentResults(student_id) {
  try {
    return await requestJson(`/results/student/${student_id}`);
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function GetStudentResult(student_id, result_id) {
  try {
    return await requestJson(`/results/student/${student_id}/${result_id}`);
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function GetMyNotices(teacher_id) {
  try {
    return await requestJson(`/my_notices/${teacher_id}`);
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function CreateNotice(notice) {
  try {
    return await requestJson("/new_notice", {
      method: "POST",
      body: {
        text: notice.text,
        teacher_id: notice.teacher_id,
        batch_codes: notice.batch_codes,
      },
    });
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function UpdateNotice(noticeId, notice) {
  try {
    return await requestJson(`/notice/${noticeId}`, {
      method: "PUT",
      body: {
        text: notice.text,
        teacher_id: notice.teacher_id,
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
    return await requestJson(`/notice/${noticeId}`, {
      method: "DELETE",
    });
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}

async function GetNoticesForStudent(student_id) {
  try {
    return await requestJson(`/notices/${student_id}`);
  } catch (error) {
    console.error(error.message);
    throw error;
  }
}