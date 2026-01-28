import { fail, redirect } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';

const API_URL = env.API_URL || "http://nadash-backend:8000";

// check if jwt is loaded or not
export const load = async ({ cookies }) => {
    const token = cookies.get('auth_token');
    if (token) {
        throw redirect(303, '/');
    }
};

export const actions = {
    default: async ({ cookies, request, fetch }) => {
        const data = await request.formData();
        const username = data.get('username') as string;
        const password = data.get('password') as string;
        let success = false;

        console.log(`[LOGIN] Proxying auth request for user: '${username}' to Python...`);

        try {
            const params = new URLSearchParams();
            params.append('username', username);
            params.append('password', password);

            const res = await fetch(`${API_URL}/token`, {
                method: 'POST',
                body: params,
                headers: {
                    'Content-Type': 'application/x-www-form-urlencoded'
                }
            });

            if (!res.ok) {
                const errData = await res.json().catch(() => ({}));
                console.log(`[LOGIN] Auth failed: ${res.status} - ${errData.detail || 'Unknown error'}`);
                
                return fail(400, { error: 'Invalid username or password' });
            }

            const tokenData = await res.json();
            const token = tokenData.access_token;

            console.log("[LOGIN] Token received from Python. Saving cookie...");

            cookies.set('auth_token', token, {
                path: '/',
                httpOnly: true,
                sameSite: 'lax',
                secure: false,
                maxAge: 3600 
            });

            return {success : true}

        } catch (error) {
            if (error.status === 302) throw error;

            console.error("[LOGIN] Connection error:", error);
            return fail(500, { error: 'Backend is offline or unreachable' });
        }
    }
};
