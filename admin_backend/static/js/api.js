const API_BASE_URL = 'http://127.0.0.1:5001/api';

let token = localStorage.getItem('token');

export function setToken(newToken) {
    token = newToken;
    localStorage.setItem('token', newToken);
}

export function getToken() {
    return token;
}

export function clearToken() {
    token = null;
    localStorage.removeItem('token');
}

export async function login(username, password) {
    const response = await fetch(`${API_BASE_URL}/login`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ username, password })
    });
    return await response.json();
}

export async function getUsers(params = {}) {
    const query = new URLSearchParams(params);
    const response = await fetch(`${API_BASE_URL}/users?${query}`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return await response.json();
}

export async function getUser(userId) {
    const response = await fetch(`${API_BASE_URL}/users/${userId}`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return await response.json();
}

export async function createUser(user) {
    const response = await fetch(`${API_BASE_URL}/users`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(user)
    });
    return await response.json();
}

export async function updateUser(userId, user) {
    const response = await fetch(`${API_BASE_URL}/users/${userId}`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(user)
    });
    return await response.json();
}

export async function deleteUser(userId) {
    const response = await fetch(`${API_BASE_URL}/users/${userId}`, {
        method: 'DELETE',
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return await response.json();
}

export async function toggleUserStatus(userId) {
    const response = await fetch(`${API_BASE_URL}/users/${userId}/status`, {
        method: 'PUT',
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return await response.json();
}

export async function resetPassword(userId, password) {
    const response = await fetch(`${API_BASE_URL}/users/${userId}/password`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ password })
    });
    return await response.json();
}

export async function getRoles() {
    const response = await fetch(`${API_BASE_URL}/roles`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return await response.json();
}

export async function getPredictions(params = {}) {
    const query = new URLSearchParams(params);
    const response = await fetch(`${API_BASE_URL}/predictions?${query}`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return await response.json();
}

export async function getPrediction(recordId) {
    const response = await fetch(`${API_BASE_URL}/predictions/${recordId}`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return await response.json();
}

export async function deletePrediction(recordId) {
    const response = await fetch(`${API_BASE_URL}/predictions/${recordId}`, {
        method: 'DELETE',
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return await response.json();
}

export async function batchDeletePredictions(ids) {
    const response = await fetch(`${API_BASE_URL}/predictions/batch_delete`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ ids })
    });
    return await response.json();
}

export async function exportPredictions(params = {}) {
    const query = new URLSearchParams(params);
    const response = await fetch(`${API_BASE_URL}/predictions/export?${query}`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return response;
}

export async function getModels(params = {}) {
    const query = new URLSearchParams(params);
    const response = await fetch(`${API_BASE_URL}/models?${query}`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return await response.json();
}

export async function getModel(modelId) {
    const response = await fetch(`${API_BASE_URL}/models/${modelId}`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return await response.json();
}

export async function activateModel(modelId) {
    const response = await fetch(`${API_BASE_URL}/models/${modelId}/activate`, {
        method: 'PUT',
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return await response.json();
}

export async function deleteModel(modelId) {
    const response = await fetch(`${API_BASE_URL}/models/${modelId}`, {
        method: 'DELETE',
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return await response.json();
}

export async function uploadModel(formData) {
    const response = await fetch(`${API_BASE_URL}/models`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`
        },
        body: formData
    });
    return await response.json();
}

export async function getSystemInfo() {
    const response = await fetch(`${API_BASE_URL}/system/info`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return await response.json();
}

export async function updateSystemInfo(info) {
    const response = await fetch(`${API_BASE_URL}/system/info`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(info)
    });
    return await response.json();
}

export async function getThreshold() {
    const response = await fetch(`${API_BASE_URL}/system/threshold`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return await response.json();
}

export async function setThreshold(threshold) {
    const response = await fetch(`${API_BASE_URL}/system/threshold`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ threshold })
    });
    return await response.json();
}

export async function getMaintenanceStatus() {
    const response = await fetch(`${API_BASE_URL}/system/maintenance`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return await response.json();
}

export async function setMaintenanceStatus(maintenanceMode) {
    const response = await fetch(`${API_BASE_URL}/system/maintenance`, {
        method: 'PUT',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ maintenance_mode: maintenanceMode })
    });
    return await response.json();
}

export async function getDashboardData() {
    const response = await fetch(`${API_BASE_URL}/statistics/dashboard`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return await response.json();
}

export async function getPredictionCount() {
    const response = await fetch(`${API_BASE_URL}/statistics/prediction_count`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return await response.json();
}

export async function getPredictionTrend(period = 'week') {
    const response = await fetch(`${API_BASE_URL}/statistics/trend?period=${period}`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return await response.json();
}

export async function getUserActivity(days = 30) {
    const response = await fetch(`${API_BASE_URL}/statistics/user_activity?days=${days}`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return await response.json();
}

export async function getModelPerformance() {
    const response = await fetch(`${API_BASE_URL}/statistics/model_performance`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return await response.json();
}

export async function generateReport(format = 'pdf') {
    const response = await fetch(`${API_BASE_URL}/statistics/report?format=${format}`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return response;
}

export async function getOperationLogs(params = {}) {
    const query = new URLSearchParams(params);
    const response = await fetch(`${API_BASE_URL}/logs/operations?${query}`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return await response.json();
}

export async function getLoginLogs(params = {}) {
    const query = new URLSearchParams(params);
    const response = await fetch(`${API_BASE_URL}/logs/logins?${query}`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return await response.json();
}

export async function getErrorLogs(params = {}) {
    const query = new URLSearchParams(params);
    const response = await fetch(`${API_BASE_URL}/logs/errors?${query}`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return await response.json();
}

export async function cleanupLogs(days = 30) {
    const response = await fetch(`${API_BASE_URL}/logs/cleanup`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({ days })
    });
    return await response.json();
}

export async function getBatchTasks(params = {}) {
    const query = new URLSearchParams(params);
    const response = await fetch(`${API_BASE_URL}/batch_tasks?${query}`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return await response.json();
}

export async function getBatchTask(taskId) {
    const response = await fetch(`${API_BASE_URL}/batch_tasks/${taskId}`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return await response.json();
}

export async function cancelBatchTask(taskId) {
    const response = await fetch(`${API_BASE_URL}/batch_tasks/${taskId}/cancel`, {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return await response.json();
}

export async function deleteBatchTask(taskId) {
    const response = await fetch(`${API_BASE_URL}/batch_tasks/${taskId}`, {
        method: 'DELETE',
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return await response.json();
}

export async function downloadBatchResult(taskId) {
    const response = await fetch(`${API_BASE_URL}/batch_tasks/${taskId}/download`, {
        headers: {
            'Authorization': `Bearer ${token}`
        }
    });
    return response;
}