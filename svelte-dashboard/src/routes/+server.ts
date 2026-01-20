import { env } from '$env/dynamic/private'; // Change to dynamic
import { json } from '@sveltejs/kit';
import { networkInterfaces } from 'os';

const nets = networkInterfaces();
let localIpAddress: string | undefined;

for (const name of Object.keys(nets)) {
    for (const net of nets[name]!) {
        if (net.family === 'IPv4' && !net.internal) {
            localIpAddress = net.address;
            break;
        }
    }
    if (localIpAddress) {
        break;
    }
}

export async function GET() {
    const backendUrl = env.API_URL || '{localIpAddress}:8000';
    
    try {
        const res = await fetch(`${backendUrl}/history`);
        const history = await res.json();
        return json({ history });
    } catch (error) {
        console.error("Dashboard API Error:", error);
        return json({ history: [] });
    }
}
