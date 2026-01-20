<script lang="ts">
  import { onMount } from 'svelte';
  import Chart from 'chart.js/auto';

  // --- Configuration ---
  let api_host = '';
  let api_url = '';

  // --- State ---
  let scoreChartCanvas: HTMLCanvasElement;
  let protoChartCanvas: HTMLCanvasElement;
  let scoreChart: Chart;
  let protoChart: Chart;

  // Default state
  let data = {
    status: "CONNECTING...",
    score: 0.0,
    interface: "---",
    model: "---",
    metrics: { cpu: 0, mbps: 0, pps: 0 },
    flow_data: { top_ips: [], protocols: [] },
    history: []
  };

  let isOffline = true;
  let maxFlowBytes = 1; 

  // --- Charts Logic ---
  function initCharts() {
    // 1. Anomaly Trend (Line Chart)
    scoreChart = new Chart(scoreChartCanvas, {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          label: 'Anomaly Score',
          data: [],
          borderColor: '#60A5FA', 
          backgroundColor: 'rgba(96, 165, 250, 0.1)',
          fill: true,
          tension: 0.4,
          pointRadius: 0,
          borderWidth: 2
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 0 },
        plugins: { legend: { display: false } },
        scales: {
          x: { display: false },
          y: { 
            beginAtZero: true, 
            max: 1.0, 
            grid: { color: '#374151' }, 
            ticks: { color: '#9CA3AF' } 
          }
        }
      }
    });

    // 2. Protocol Distribution (Doughnut Chart)
    protoChart = new Chart(protoChartCanvas, {
      type: 'doughnut',
      data: {
        labels: ['TCP', 'UDP', 'ICMP', 'Other'],
        datasets: [{
          data: [0, 0, 0, 0],
          backgroundColor: ['#3B82F6', '#10B981', '#F59E0B', '#6B7280'],
          borderWidth: 0
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '75%',
        plugins: { 
          legend: { 
            position: 'right', 
            labels: { color: '#9CA3AF', font: { size: 10 } } 
          } 
        }
      }
    });
  }

  function updateCharts() {
    if (!scoreChart || !protoChart) return;

    // Safety: Ensure history exists
    const history = data.history || [];
    
    // 1. Update Line Chart
    if (history.length > 0) {
        scoreChart.data.labels = history.map(d => d.time);
        scoreChart.data.datasets[0].data = history.map(d => d.score);
        
        // Dynamic Threat Coloring
        const currentScore = data.score || 0;
        const isCritical = currentScore > 0.7;
        
        scoreChart.data.datasets[0].borderColor = isCritical ? '#EF4444' : '#60A5FA'; 
        scoreChart.data.datasets[0].backgroundColor = isCritical ? 'rgba(239, 68, 68, 0.2)' : 'rgba(96, 165, 250, 0.1)';
        scoreChart.update();
    }

    // 2. Update Protocol Chart
    const protocols = data.flow_data?.protocols || [];
    if (protocols.length > 0) {
        const labels = protocols.map(p => p.label);
        const values = protocols.map(p => p.value);
        
        if (values.some(v => v > 0)) {
            protoChart.data.labels = labels;
            protoChart.data.datasets[0].data = values;
            protoChart.update();
        }
    }

    // 3. Update Max Flow Bytes for progress bars
    const topIps = data.flow_data?.top_ips || [];
    if (topIps.length > 0) {
      const maxVal = Math.max(...topIps.map(ip => ip.value));
      maxFlowBytes = maxVal > 0 ? maxVal : 1; 
    }
  }

  // --- Data Fetching ---
  async function fetchData() {
    if (!api_url) return;
    try {
      const res = await fetch(api_url);
      const json = await res.json();
      
      if (json && json.timestamp) {
        // Preserve old history
        const previousHistory = data.history || [];

        // Update state
        data = json;
        isOffline = false;

        // Manually append new score (Client-side buffer)
        const newPoint = {
            time: new Date().toLocaleTimeString([], { hour12: false }),
            score: data.score
        };
        // Keep last 20 points
        data.history = [...previousHistory, newPoint].slice(-20);

        updateCharts();
      }
    } catch (e) {
      console.error("Fetch error:", e);
      isOffline = true;
      data.status = "OFFLINE";
    }
  }

  onMount(() => {
    // Dynamic Host Discovery
    api_host = window.location.hostname;
    // api_url = `http://${api_host}:8000/dashboard`;
    api_url = `api/dashboard`;

    initCharts();
    fetchData();
    const interval = setInterval(fetchData, 1000);

    return () => {
      clearInterval(interval);
      if (scoreChart) scoreChart.destroy();
      if (protoChart) protoChart.destroy();
    };
  });
</script>

<div class="min-h-screen bg-gray-900 text-white font-mono p-6 selection:bg-blue-500 selection:text-white">
  
  <nav class="flex justify-between items-center mb-8 bg-gray-800 p-4 rounded-xl shadow-lg border border-gray-700/50 backdrop-blur-sm">
    <div class="flex items-center gap-4">
      <div class="h-10 w-10 bg-blue-600 rounded-lg flex items-center justify-center shadow-lg shadow-blue-500/20">
        <svg class="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z"></path></svg>
      </div>
      <div>
        <h1 class="text-lg font-bold tracking-tight text-white">NADash</h1>
        <div class="flex items-center gap-2 text-xs text-gray-400">
          <span class="bg-gray-700 px-2 py-0.5 rounded text-gray-300 font-semibold">{data.interface}</span>
          <span>•</span>
          <span class="text-blue-400">{data.model}</span>
        </div>
      </div>
    </div>

    <div class="flex items-center gap-4">
      <div class="text-right hidden sm:block">
        <p class="text-[10px] text-gray-500 font-bold uppercase tracking-wider">System Status</p>
        <p class="font-bold {data.status === 'CRITICAL' ? 'text-red-500' : (isOffline ? 'text-gray-500' : 'text-emerald-400')}">
          {data.status}
        </p>
      </div>
      <div class="relative">
        <div class="h-3 w-3 rounded-full {data.status === 'CRITICAL' ? 'bg-red-500' : 'bg-emerald-500'} animate-pulse"></div>
        {#if data.status === 'CRITICAL'}
          <div class="absolute -inset-1 rounded-full bg-red-500 opacity-20 animate-ping"></div>
        {/if}
      </div>
    </div>
  </nav>

  <div class="grid grid-cols-1 lg:grid-cols-4 gap-6">

    <div class="lg:col-span-1 space-y-6">
      
      <div class="bg-gray-800 p-6 rounded-2xl border border-gray-700 shadow-xl relative overflow-hidden group">
        <div class="absolute top-0 left-0 w-1 h-full transition-colors duration-300 {data.score > 0.7 ? 'bg-red-500' : 'bg-blue-500'}"></div>
        
        <div class="flex justify-between items-start mb-2">
            <h3 class="text-gray-400 text-[10px] font-bold uppercase tracking-wider">Anomaly Probability</h3>
            <svg class="w-5 h-5 text-gray-600 group-hover:text-blue-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
        </div>
        
        <div class="flex items-baseline gap-2">
          <span class="text-5xl font-bold text-white tracking-tighter">{(data.score * 100).toFixed(0)}</span>
          <span class="text-xl text-gray-500">%</span>
        </div>
        
        <div class="mt-4 h-1.5 w-full bg-gray-700 rounded-full overflow-hidden">
             <div class="h-full transition-all duration-500 {data.score > 0.7 ? 'bg-red-500' : 'bg-blue-500'}" style="width: {data.score * 100}%"></div>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4">
        <div class="bg-gray-800 p-4 rounded-xl border border-gray-700 hover:border-gray-600 transition-colors">
          <div class="flex items-center gap-2 mb-2">
             <div class="p-1.5 bg-gray-700 rounded-md">
                <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"></path></svg>
             </div>
             <p class="text-gray-500 text-[10px] font-bold">CPU LOAD</p>
          </div>
          <p class="text-2xl font-bold text-white">{data.metrics.cpu}%</p>
        </div>

        <div class="bg-gray-800 p-4 rounded-xl border border-gray-700 hover:border-gray-600 transition-colors">
          <div class="flex items-center gap-2 mb-2">
             <div class="p-1.5 bg-gray-700 rounded-md">
                <svg class="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4"></path></svg>
             </div>
             <p class="text-gray-500 text-[10px] font-bold">PKTS/SEC</p>
          </div>
          <p class="text-2xl font-bold text-white">{data.metrics.pps}</p>
        </div>

        <div class="bg-gray-800 p-4 rounded-xl border border-gray-700 col-span-2 hover:border-gray-600 transition-colors">
          <div class="flex justify-between items-center mb-1">
             <p class="text-gray-500 text-[10px] font-bold uppercase">Network Traffic</p>
             <span class="text-[10px] text-blue-400 bg-blue-400/10 px-2 py-0.5 rounded">Rx Only</span>
          </div>
          <p class="text-3xl font-bold text-white tracking-tight">{data.metrics.mbps} <span class="text-sm text-gray-500 font-normal">Mbps</span></p>
        </div>
      </div>
    </div>

    <div class="lg:col-span-2 bg-gray-800 p-6 rounded-2xl border border-gray-700 shadow-xl flex flex-col">
      <div class="flex justify-between items-center mb-6">
        <div>
           <h3 class="text-white font-bold text-lg">Real-time Threat Analysis</h3>
           <p class="text-xs text-gray-500">Live inference stream from the {data.model} model</p>
        </div>
        <div class="flex items-center gap-2">
           <span class="w-2 h-2 rounded-full bg-red-500 animate-pulse"></span>
           <span class="text-xs text-gray-400 font-mono">LIVE</span>
        </div>
      </div>
      <div class="flex-grow w-full relative min-h-[250px]">
        <canvas bind:this={scoreChartCanvas}></canvas>
      </div>
    </div>

    <div class="lg:col-span-1 space-y-6">
      
      <div class="bg-gray-800 p-6 rounded-2xl border border-gray-700 shadow-xl">
        <h3 class="text-gray-400 text-[10px] font-bold uppercase tracking-wider mb-4 border-b border-gray-700 pb-2">Protocol Mix</h3>
        <div class="h-32 relative">
            <canvas bind:this={protoChartCanvas}></canvas>
            
            {#if (!data.flow_data?.protocols || data.flow_data.protocols.length === 0)}
              <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
                <span class="text-xs text-gray-600 italic">No Data</span>
              </div>
            {:else}
              <div class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                  <span class="text-2xl font-bold text-white">{data.flow_data.protocols.length}</span>
                  <span class="text-[10px] text-gray-500">TYPES</span>
              </div>
            {/if}
        </div>
      </div>

      <div class="bg-gray-800 p-6 rounded-2xl border border-gray-700 shadow-xl flex-grow">
        <div class="flex justify-between items-center mb-4 border-b border-gray-700 pb-2">
            <h3 class="text-gray-400 text-[10px] font-bold uppercase tracking-wider">Top Source IPs</h3>
            <span class="text-[10px] text-gray-500">By Vol</span>
        </div>
        
        <div class="space-y-4">
            {#if (!data.flow_data?.top_ips || data.flow_data.top_ips.length === 0)}
                <div class="flex flex-col items-center justify-center h-32 text-gray-600">
                    <svg class="w-8 h-8 mb-2 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18.364 18.364A9 9 0 005.636 5.636m12.728 12.728A9 9 0 015.636 5.636m12.728 12.728L5.636 5.636"></path></svg>
                    <p class="text-xs italic">Waiting for flows...</p>
                </div>
            {:else}
                {#each data.flow_data.top_ips as ip}
                    <div>
                        <div class="flex justify-between items-center text-xs mb-1">
                            <span class="text-gray-300 font-mono tracking-wide">{ip.label}</span>
                            <span class="text-gray-500">{ip.value.toFixed(0)} B/s</span>
                        </div>
                        <div class="w-full h-1.5 bg-gray-700/50 rounded-full overflow-hidden">
                            <div class="h-full bg-gradient-to-r from-blue-600 to-blue-400 rounded-full" 
                                 style="width: {(ip.value / maxFlowBytes) * 100}%"></div>
                        </div>
                    </div>
                {/each}
            {/if}
        </div>
      </div>

    </div>
  </div>
</div>
