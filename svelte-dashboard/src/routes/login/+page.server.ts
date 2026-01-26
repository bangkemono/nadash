import { fail, redirect } from '@sveltejs/kit';
import { env } from '$env/dynamic/private';

const API_URL = env.API_URL || "http://nadash-backend:8000";

export const actions = {
    default: async ({ request, fetch }) => {
        const data = await request.formData();
        const username = data.get('username') as string;
        const password = data.get('password') as string;

        console.log(`[LOGIN] Proxying auth request for user: '${username}' to Python...`);

        try {
            const params = new URLSearchParams();
            params.append('username', username);
            params.append('password', password);

            const res = await fetch(`${API_URL}/token`, {
                method: 'POST',
                body: params,
                headers: { 'Content-Type': 'application/x-www-form-urlencoded' }
            });

            if (!res.ok) {
                return fail(400, { error: 'Invalid username or password' });
            }

            const tokenData = await res.json();
            return {
                success: true,
                token: tokenData.access_token
            }

        } catch (error) {
            console.error("[LOGIN] Connection error:", error);
            return fail(500, { error: 'Backend is offline or unreachable' });
        }
    }
};
