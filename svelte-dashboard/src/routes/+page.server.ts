import { env } from '$env/dynamic/private';

export const load = async ({ fetch }) => {
  // FIX: Use Docker Service Name as default. 
  // We use "http://" because fetch requires a protocol.
  const backendUrl = env.API_URL || "http://aiops-engine:8000";

  console.log(`[SERVER] Connecting to backend at: ${backendUrl}`);

  try {
    // Note: Your python backend uses "/dashboard", not "/status"
    const res = await fetch(`${backendUrl}/dashboard`);
    
    if (!res.ok) {
      throw new Error(`Backend returned status ${res.status}`);
    }

    const data = await res.json();
    return {
      health: data
    };
  } catch (error) {
    console.error("[SERVER] Failed to fetch system status:", error);
    
    // Return safe default so page loads even if backend is down
    return { 
      health: { 
        status: "UNREACHABLE", 
        score: 0,
        interface: "---",
        model: "---",
        metrics: { cpu: 0, mbps: 0, pps: 0 },
        flow_data: { top_ips: [], protocols: [] },
        history: []
      } 
    };
  }
};

