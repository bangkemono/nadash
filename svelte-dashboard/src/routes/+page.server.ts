import { env } from '$env/dynamic/private';

export const load = async ({ fetch }) => {
  const backendUrl = env.API_URL || "http://aiops-engine:8000";

  console.log(`[SERVER] Connecting to backend at: ${backendUrl}`);

  try {
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

