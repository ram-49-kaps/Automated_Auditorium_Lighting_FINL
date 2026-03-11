
const API_BASE_URL = '/api';

/**
 * Upload a script file to the backend
 * @param {File} file - The file object to upload
 * @returns {Promise<Object>} - Format: { job_id: "...", filename: "..." }
 */
export async function uploadScript(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/upload`, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        throw new Error(`Upload failed: ${response.statusText}`);
    }

    return response.json();
}

/**
 * Validate a script file with the backend before starting the pipeline
 * @param {File} file - The file object to validate
 * @returns {Promise<Object>} - Format: { valid: boolean, doc_type: "...", confidence: float, reason: "..." }
 */
export async function validateScript(file) {
    const formData = new FormData();
    formData.append('file', file);

    const response = await fetch(`${API_BASE_URL}/validate`, {
        method: 'POST',
        body: formData,
    });

    if (!response.ok) {
        throw new Error(`Validation failed: ${response.statusText}`);
    }

    return response.json();
}
/**
 * Fetch the final results for a job
 * @param {string} jobId 
 * @returns {Promise<Object>}
 */
export async function getResults(jobId) {
    const response = await fetch(`${API_BASE_URL}/results/${jobId}`);
    if (!response.ok) {
        throw new Error(`Failed to fetch results: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Launch the 3D simulation
 * @param {string} jobId 
 * @returns {Promise<Object>} - Format: { status: "launched", url: "..." }
 */
export async function launchSimulation(jobId) {
    const response = await fetch(`${API_BASE_URL}/launch/${jobId}`, {
        method: 'POST',
    });
    if (!response.ok) {
        throw new Error(`Simulation launch failed: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Re-process an already-uploaded script (no re-upload needed)
 * @param {string} jobId 
 * @returns {Promise<Object>} - Format: { job_id: "...", status: "reprocessing_started" }
 */
export async function reprocessScript(jobId) {
    const response = await fetch(`${API_BASE_URL}/reprocess/${jobId}`, {
        method: 'POST',
    });
    if (!response.ok) {
        throw new Error(`Reprocess failed: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Get the download URL for the lighting instructions
 * @param {string} jobId 
 * @returns {string}
 */
export function getDownloadUrl(jobId) {
    return `${API_BASE_URL}/download/${jobId}`;
}

/**
 * Fetch Phase 7 evaluation metrics for a job
 * @param {string} jobId 
 * @returns {Promise<Object>}
 */
export async function getMetrics(jobId) {
    const response = await fetch(`${API_BASE_URL}/metrics/${jobId}`);
    if (!response.ok) {
        throw new Error(`Failed to fetch metrics: ${response.statusText}`);
    }
    return response.json();
}

/**
 * Tell the backend to resolve an AI prediction and overwrite the JSON
 * @param {string} jobId 
 * @param {string} sceneId
 * @param {string} rule
 */
export async function applyResolution(jobId, sceneId, rule) {
    const response = await fetch(`${API_BASE_URL}/apply-resolution/${jobId}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({ scene_id: sceneId, rule: rule })
    });
    if (!response.ok) {
        throw new Error(`Failed to apply resolution: ${response.statusText}`);
    }
    return response.json();
}
