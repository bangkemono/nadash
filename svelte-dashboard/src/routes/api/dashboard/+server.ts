import { env } from '$env/dynamic/private';
import { json } from '@sveltejs/kit';

const API_URL = env.API_URL || "http://nadash-backend:8000";

export async function GET({ request, fetch }) {
    // fetch Authorization header
    const authHeader = request.headers.get('Authorization');

    if (!authHeader) {
        return json({ status: "UNAUTHORIZED" }, { status: 401 });
    }

    try {
        // pass to python
        const res = await fetch(`${API_URL}/dashboard`, {
            headers: {
                'Authorization': authHeader
            }
        });

        if (res.status === 401) {
            return json({ status: "EXPIRED" }, { status: 401 });
        }

        const data = await res.json();
        return json(data);

    } catch (e) {
        return json({ status: "OFFLINE" }, { status: 500 });
    }
}

