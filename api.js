const api_url = "https://educoffee.onrender.com/api";
// const api_url = "http://127.0.0.1:8000/api";

async function Register(data) {
  try {
    const response = await fetch(`${api_url}/register`, {
      method: "POST",
      headers: {
        "Content-type": "application/json",
      },
      body: JSON.stringify({
        name: data.name,
        email: data.email,
        password: data.password,
        phone: data.phone,
        center_name: data.center_name,
        role: data.role,
        batch_codes: data.batch_codes,
        plan: data.plan
      }),
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail);
    }

    const result = await response.json();
    console.log(result);
    return result;
  } catch (error) {
    console.log(error.message);
    throw error;
  }
}

async function GetUserByID(id) {
  try {
    const response = await fetch(`${api_url}/user/${id}`, {
      method: "GET",
      headers: {
        "Content-type": "application/json",
      },
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail);
    }

    const data = await response.json();
    console.log(data);
    return data;
  } catch (error) {
    console.log(error.message);
    throw error;
  }
}

async function Login(email, pass) {
  try {
    const response = await fetch(`${api_url}/login`, {
      method: "POST",
      headers: {
        "Content-type": "application/json",
      },
      body: JSON.stringify({
        email: email,
        password: pass,
      }),
    });
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail);
    }
    const data = await response.json();
    console.log(data);
    return data;
  } catch (err) {
    console.log(err.message);
    throw err;
  }
}

async function CreateNewBatch(batch) {
  try {
    const response = await fetch(`${api_url}/new_batch`, {
      method: "POST",
      headers: {
        "Content-type": "application/json",
      },
      body: JSON.stringify({
        name: batch.name,
        year: batch.year,
        schedule: batch.schedule,
        teacher_id: batch.teacher_id,
        code: batch.code,
      }),
    });
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail);
    }
    const data = await response.json();
    console.log(data);
    return data;
  } catch (err) {
    console.log(err.message);
    throw err;
  }
}

async function UpdateBatch(code, batch) {
  try {
    const response = await fetch(`${api_url}/batch/${code}`, {
      method: "PUT",
      headers: {
        "Content-type": "application/json",
      },
      body: JSON.stringify({
        name: batch.name,
        year: batch.year,
        schedule: batch.schedule,
      }),
    });
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail);
    }
    const data = await response.json();
    console.log(data);
    return data;
  } catch (err) {
    console.log(err.message);
    throw err;
  }
}

async function DeleteBatch(code) {
  try {
    const response = await fetch(`${api_url}/batch/${code}`, {
      method: "DELETE",
      headers: {
        "Content-type": "application/json",
      },
    });
    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail);
    }
    return true;
  } catch (err) {
    console.log(err.message);
    throw err;
  }
}

async function GetBatchesByTID(teacher_id) {
  try {
    const response = await fetch(`${api_url}/batches/${teacher_id}`, {
      method: "GET",
      headers: {
        "Content-type": "application/json",
      },
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail);
    }
    const data = await response.json();
    console.log(data);
    return data;
  } catch (err) {
    console.log(err.message);
    throw err;
  }
}

async function GetMyStudents(teacher_id) {
  try {
    const response = await fetch(`${api_url}/my_students/${teacher_id}`, {
      method: "GET",
      headers: {
        "Content-type": "application/json",
      },
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail);
    }
    const data = await response.json();
    console.log(data);
    return data;
  } catch (err) {
    console.log(err.message);
    throw err;
  }
}

async function GetStudentsByBC(batch_code) {
  try {
    const response = await fetch(`${api_url}/students_in_batch/${batch_code}`, {
      method: "GET",
      headers: {
        "Content-type": "application/json",
      },
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail);
    }
    const data = await response.json();
    console.log(data);
    return data;
  } catch (err) {
    console.log(err.message);
    throw err;
  }
}

async function CreateResult(result) {
  try {
    const response = await fetch(`${api_url}/new_result`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        title: result.title,
        description: result.description,
        total_marks: result.total_marks,
        batch_code: result.batch_code,
        scores: result.scores
      })
    });

    if (!response.ok) {
      const err = await response.json();
      console.log("FASTAPI ERROR:", err);
      throw new Error(err.detail);
    }

    return await response.json();

  } catch (err) {
    console.log("CLIENT ERROR:", err.message);
    throw err;
  }
}

async function GetStudentResults(student_id) {
  try {
    const response = await fetch(`${api_url}/results/student/${student_id}`, {
      method: "GET",
      headers: {
        "Content-type": "application/json",
      },
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail);
    }
    const data = await response.json();
    console.log(data);
    return data;
  } catch (err) {
    console.log(err.message);
    throw err;
  }
}

async function GetStudentResult(student_id, result_id) {
  try {
    const response = await fetch(`${api_url}/results/student/${student_id}/${result_id}`, {
      method: "GET",
      headers: {
        "Content-type": "application/json",
      },
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail);
    }
    const data = await response.json();
    console.log(data);
    return data;
  } catch (err) {
    console.log(err.message);
    throw err;
  }
}

async function GetMyNotices(teacher_id) {
  try {
    const response = await fetch(`${api_url}/my_notices/${teacher_id}`, {
      method: "GET",
      headers: {
        "Content-type": "application/json",
      },
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail);
    }
    const data = await response.json();
    console.log(data);
    return data;
  } catch (err) {
    console.log(err.message);
    throw err;
  }
}

async function CreateNotice(notice) {
  console.log(notice.text)
  try {
    const response = await fetch(`${api_url}/new_notice`, {
      method: "POST",
      headers: {
        "Content-type": "application/json",
      },
      body: JSON.stringify({
        text: notice.text,
        teacher_id: notice.teacher_id,
        batch_codes: notice.batch_codes,
      })
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail);
    }
    const data = await response.json();
    console.log(data);
    return data;
  } catch (err) {
    console.log(err.message);
    throw err;
  }
}

async function UpdateNotice(noticeId, notice) {
  try {
    const response = await fetch(`${api_url}/notice/${noticeId}`, {
      method: "PUT",
      headers: {
        "Content-type": "application/json",
      },
      body: JSON.stringify({
        text: notice.text,
        teacher_id: notice.teacher_id,
        batch_codes: notice.batch_codes,
      })
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail);
    }

    return await response.json();
  } catch (err) {
    console.log(err.message);
    throw err;
  }
}

async function DeleteNotice(noticeId) {
  try {
    const response = await fetch(`${api_url}/notice/${noticeId}`, {
      method: "DELETE",
      headers: {
        "Content-type": "application/json",
      },
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail);
    }

    return true;
  } catch (err) {
    console.log(err.message);
    throw err;
  }
}

async function GetNoticesForStudent(student_id) {
  try {
    const response = await fetch(`${api_url}/notices/${student_id}`, {
      method: "GET",
      headers: {
        "Content-type": "application/json",
      },
    });

    if (!response.ok) {
      const err = await response.json();
      throw new Error(err.detail);
    }
    const data = await response.json();
    console.log(data);
    return data;
  } catch (err) {
    console.log(err.message);
    throw err;
  }
}