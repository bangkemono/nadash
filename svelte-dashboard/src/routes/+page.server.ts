import { env } from '$env/dynamic/private';
import { redirect } from '@sveltejs/kit';
import jwt from 'jsonwebtoken';

const BACKEND_URL = env.API_URL || "http://nadash-backend:8000";

export const load = async ({ cookies, fetch }) => {
    // get auth_token from cookie
    const token = cookies.get('auth_token');

    if (!token) {
        throw redirect(302, '/login');
    }

    let userDisplay = { name: "Unknown" };
    try {
        const decoded = jwt.decode(token) as any;
        userDisplay = { name: decoded?.name || decoded?.sub || "User" };
    } catch (e) {}

    let healthData = { status: "CONNECTING..." };

    try {
        // fetch data from api/dashboard using jwt header
        const res = await fetch(`${BACKEND_URL}/dashboard`, {
            headers: {
                'Authorization': `bearer ${token}`
            }
        });

        if (res.status === 401) {
            console.log("[DASHBOARD] Token expired/invalid. Redirecting.");
            cookies.delete('auth_token', { path: '/' });
            throw redirect(302, '/login');
        }
        if (res.ok) {
            healthData = await res.json();
        }
    } catch (error) {
        if (error.status === 302) throw error;
        console.error("[DASHBOARD] Backend offline:", error);
        healthData.status = "UNREACHABLE";
    }
    return {
        user: userDisplay,
        health: healthData
    };
};
