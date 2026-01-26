import { env } from '$env/dynamic/private';
import { json } from '@sveltejs/kit';

const API_URL = env.API_URL || "http://nadash-backend:8000";

export async function GET({ cookies, fetch }) {
    // fetch auth_token for json data authorization
    const token = cookies.get('auth_token');

    if (!token) {
        return json({ status: "UNAUTHORIZED" }, { status: 401 });
    }

    try {
        const res = await fetch(`${API_URL}/dashboard`, {
            headers: {
                'Authorization': `Bearer ${token}`
            }
        });

        if (res.status === 401) {
            cookies.delete('auth_token', { path: '/' });
            return json({ status: "EXPIRED" }, { status: 401 });
        }

        const data = await res.json();
        return json(data);

    } catch (error) {
        console.error("[API Proxy] Connection failed:", error);
        return json({ status: "OFFLINE" }, { status: 500 });
    }
}
