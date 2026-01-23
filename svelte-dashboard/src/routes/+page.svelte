<script lang="ts">
  import { onMount } from 'svelte';
  import Chart from 'chart.js/auto';

  let api_host = '';
  let api_url = '';
  let train_url = '';

  let scoreChartCanvas: HTMLCanvasElement;
  let protoChartCanvas: HTMLCanvasElement;
  let scoreChart: Chart;
  let protoChart: Chart;

  let data = {
    status: "CONNECTING...",
    score: 0.0,
    alert: "System Normal",
    timestamp: "---",
    interface: "---",
    model: "---",
    metrics: { cpu: 0, mbps: 0, pps: 0 },
    flow_data: { top_ips: [], protocols: [] },
    history: []
  };

  let isOffline = true;
  let maxFlowBytes = 1; 
  let isTraining = false;

  function initCharts() {
    const ctx = scoreChartCanvas.getContext('2d');
    const gradient = ctx.createLinearGradient(0, 0, 0, 400);
    gradient.addColorStop(0, 'rgba(96, 165, 250, 0.6)'); 
    gradient.addColorStop(1, 'rgba(96, 165, 250, 0.0)');

    scoreChart = new Chart(scoreChartCanvas, {
      type: 'line',
      data: {
        labels: [],
        datasets: [{
          label: 'Anomaly Score',
          data: [],
          backgroundColor: gradient, // clean gradient reference
          borderColor: '#60A5FA', 
          borderWidth: 2,
          fill: true,
          tension: 0.4,
          pointRadius: 0,
          pointHoverRadius: 6,
          pointHoverBackgroundColor: '#fff'
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: { duration: 0 },
        plugins: { legend: { display: false } },
        scales: {
          x: {
            display: true,
            grid: { color: '#374151', tickLength: 4 },
            ticks: {
              color: '#9CA3AF',
              maxTicksLimit: 6,
              maxRotation: 0,
              font: { family: "'JetBrains Mono', monospace", size: 10 } 
            }
          },
          y: { 
            beginAtZero: true, 
            max: 1.0, 
            grid: { color: '#374151' }, 
            ticks: { 
                color: '#9CA3AF', 
                font: { family: "'JetBrains Mono', monospace", size: 10 } 
            } 
          }
        }
      }
    });

    protoChart = new Chart(protoChartCanvas, {
      type: 'doughnut',
      data: {
        labels: ['TCP', 'UDP', 'ICMP', 'Other'],
        datasets: [{
          data: [0, 0, 0, 0],
          backgroundColor: ['#3B82F6', '#10B981', '#F59E0B', '#6B7280'],
          borderWidth: 0,
          hoverOffset: 4
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        cutout: '75%',
        plugins: { 
          legend: { 
            position: 'right', 
            labels: { 
                color: '#9CA3AF', 
                usePointStyle: true, 
                pointStyle: 'circle',
                font: { family: "'Space Grotesk', sans-serif", size: 11 } 
            } 
          } 
        }
      }
    });
  }

  function updateCharts() {
    if (!scoreChart || !protoChart) return;

    const history = data.history || [];
    if (history.length > 0) {
        scoreChart.data.labels = history.map(d => d.time);
        scoreChart.data.datasets[0].data = history.map(d => d.score);
        
        const currentScore = data.score || 0;
        const isCritical = currentScore > 0.75;
        scoreChart.data.datasets[0].borderColor = isCritical ? '#EF4444' : '#60A5FA'; 
        
        const ctx = scoreChartCanvas.getContext('2d');
        const newGradient = ctx.createLinearGradient(0, 0, 0, 400);
        if (isCritical) {
            newGradient.addColorStop(0, 'rgba(239, 68, 68, 0.6)');
            newGradient.addColorStop(1, 'rgba(239, 68, 68, 0.0)');
        } else {
            newGradient.addColorStop(0, 'rgba(96, 165, 250, 0.6)');
            newGradient.addColorStop(1, 'rgba(96, 165, 250, 0.0)');
        }
        scoreChart.data.datasets[0].backgroundColor = newGradient;
        
        scoreChart.update();
    }

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

    const topIps = data.flow_data?.top_ips || [];
    if (topIps.length > 0) {
      const maxVal = Math.max(...topIps.map(ip => ip.value));
      maxFlowBytes = maxVal > 0 ? maxVal : 1; 
    }
  }

  async function fetchData() {
    if (!api_url) return;
    try {
      const res = await fetch(api_url);
      const json = await res.json();
      if (json && json.timestamp) {
        const previousHistory = data.history || [];
        data = json;
        isOffline = false;

        const newPoint = {
            time: new Date().toLocaleTimeString([], { hour12: false }),
            score: data.score
        };
        data.history = [...previousHistory, newPoint].slice(-60);

        updateCharts();
      }
    } catch (e) {
      console.error("Fetch error:", e);
      isOffline = true;
      data.status = "OFFLINE";
    }
  }

  async function retrainModel() {
    if (isTraining) return;
    isTraining = true;
    try {
        const res = await fetch('/api/train/retrain-recent', { method: 'POST' });
        const result = await res.json();
        alert(`AI Update: ${result.message}`);
    } catch (e) {
        alert("Failed to retrain model");
    } finally {
        isTraining = false;
    }
  }

  onMount(() => {
    api_host = window.location.hostname;
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

  <div class="min-h-screen text-white font-sans tracking-tight p-6 selection:bg-blue-500 selection:text-white" style="background-color: #030712; /* gray-950 */ background-image: linear-gradient(rgba(59, 130, 246, 0.15) 1px, transparent 1px), linear-gradient(90deg, rgba(59, 130, 246, 0.15) 1px, transparent 1px); background-size: 40px 40px;">
  <nav class="relative flex flex-col md:flex-row justify-between items-center mb-8 bg-gray-800/80 p-4 rounded-xl shadow-2xl border border-gray-700 backdrop-blur-md gap-4 overflow-hidden">
    <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-blue-500 to-transparent opacity-50"></div>

    <div class="flex items-center gap-4 w-full md:w-auto">
      <div class="group relative flex h-10 w-10 items-center justify-center overflow-hidden rounded-lg bg-gray-800 border border-blue-500/30 shadow-[0_0_10px_rgba(59,130,246,0.3)]">
           <div class="absolute inset-0 bg-blue-500/10 group-hover:bg-blue-500/20 transition-colors"></div>
                <svg class="relative h-8 w-8 text-blue-500 drop-shadow-[0_0_5px_rgba(59,130,246,0.8)]" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 2l9 4.9V17.1L12 22 3 17.1V6.9L12 2z" />
                  <circle cx="12" cy="12" r="3" class="fill-blue-400/20 stroke-blue-400" />
                  <path stroke-linecap="round" stroke-linejoin="round" d="M12 2v4 M12 22v-4" class="opacity-50" />
                </svg>
      </div>
      <div>
        <h1 class="text-lg font-bold tracking-tighter text-white">NADash</h1>
        <div class="flex items-center gap-2 text-xs text-gray-400">
          <span class="bg-gray-700/50 px-2 py-0.5 rounded text-gray-300 font-medium font-mono border border-gray-600">{data.interface}</span>
          <span>•</span>
          <span class="text-blue-400 font-medium tracking-normal">{data.model}</span>
        </div>
      </div>
    </div>

    {#if data.alert && data.alert !== "System Normal"}
        <div class="flex-grow mx-4 px-4 py-2 bg-red-500/10 border border-red-500/50 rounded text-center animate-pulse shadow-[0_0_20px_rgba(239,68,68,0.2)]">
            <span class="text-red-400 font-bold text-sm uppercase tracking-wider">⚠️ {data.alert}</span>
        </div>
    {/if}

    <div class="flex items-center gap-4 w-full md:w-auto justify-end">
        <button 
            on:click={retrainModel}
            disabled={isTraining}
            class="px-3 py-1.5 text-xs font-bold border border-gray-600 rounded hover:bg-gray-700 hover:border-blue-400 hover:shadow-[0_0_10px_rgba(96,165,250,0.2)] active:scale-95 transition-all text-gray-300 disabled:opacity-50"
        >
            {isTraining ? 'LEARNING...' : 'FALSE POSITIVE?'}
        </button>

      <div class="text-right hidden sm:block">
        <p class="text-[10px] text-gray-500 font-bold uppercase tracking-wider">System Status</p>
        <p class="font-bold font-mono tracking-normal {data.status === 'CRITICAL' ? 'text-red-500 drop-shadow-[0_0_5px_rgba(239,68,68,0.8)]' : (isOffline ? 'text-gray-500' : 'text-emerald-400 drop-shadow-[0_0_5px_rgba(52,211,153,0.5)]')}">
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
      <div class="bg-gray-800/80 p-6 rounded-2xl border border-gray-700 shadow-xl relative overflow-hidden group backdrop-blur-sm">
        <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-blue-500 to-transparent opacity-50"></div>
        
        <div class="absolute top-0 left-0 w-1 h-full transition-colors duration-300 {data.score > 0.75 ? 'bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]' : 'bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.5)]'}"></div>
        
        <div class="flex justify-between items-start mb-2">
            <h3 class="text-gray-400 text-[10px] font-bold uppercase tracking-wider">Anomaly Probability</h3>
            <svg class="w-5 h-5 text-gray-600 group-hover:text-blue-400 transition-colors" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
        </div>
        
        <div class="flex items-baseline gap-2">
          <span class="text-5xl font-bold text-white tracking-tighter font-mono">{(data.score * 100).toFixed(0)}</span>
          <span class="text-xl text-gray-500 font-sans">%</span>
        </div>
        
        <div class="mt-4 h-1.5 w-full bg-gray-700 rounded-full overflow-hidden">
             <div class="h-full transition-all duration-500 {data.score > 0.75 ? 'bg-red-500' : 'bg-blue-500'}" style="width: {data.score * 100}%"></div>
        </div>
      </div>

      <div class="grid grid-cols-2 gap-4">
        {#each [
            { label: 'CPU LOAD', val: data.metrics.cpu + '%', icon: 'M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z' },
            { label: 'PKTS/SEC', val: data.metrics.pps, icon: 'M8 7h12m0 0l-4-4m4 4l-4 4m0 6H4m0 0l4 4m-4-4l4-4' }
        ] as metric}
        <div class="bg-gray-800/80 p-4 rounded-xl border border-gray-700 hover:border-gray-600 transition-colors relative overflow-hidden">
          <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-gray-400 to-transparent opacity-20"></div>
          <div class="flex items-center gap-2 mb-2">
             <p class="text-gray-500 text-[10px] font-bold">{metric.label}</p>
          </div>
          <p class="text-2xl font-bold text-white font-mono">{metric.val}</p>
        </div>
        {/each}

        <div class="bg-gray-800/80 p-4 rounded-xl border border-gray-700 col-span-2 hover:border-gray-600 transition-colors relative overflow-hidden">
          <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-blue-500 to-transparent opacity-30"></div>
          <div class="flex justify-between items-center mb-1">
             <p class="text-gray-500 text-[10px] font-bold uppercase">Network Traffic</p>
             <span class="text-[10px] text-blue-400 bg-blue-400/10 px-2 py-0.5 rounded font-mono border border-blue-400/20">Rx / Tx</span>
          </div>
          <p class="text-3xl font-bold text-white tracking-tight font-mono">{data.metrics.mbps} <span class="text-sm text-gray-500 font-sans font-normal">Mbps</span></p>
        </div>
      </div>
    </div>

    <div class="lg:col-span-2 bg-gray-800/80 p-6 rounded-2xl border border-gray-700 shadow-xl flex flex-col relative overflow-hidden backdrop-blur-sm">
      <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-blue-400 to-transparent opacity-60"></div>
      
      <div class="flex justify-between items-center mb-6">
        <div>
           <h3 class="text-white font-bold text-lg tracking-tight">Real-time Threat Analysis</h3>
           <p class="text-xs text-gray-500">Live inference stream</p>
        </div>
        <div class="flex items-center gap-2">
           <span class="w-2 h-2 rounded-full {data.status === 'CRITICAL' ? 'bg-red-500' : 'bg-emerald-500'} animate-pulse"></span>
           <span class="text-xs text-gray-400 font-mono font-bold tracking-wider">LIVE</span>
        </div>
      </div>
      <div class="flex-grow w-full relative min-h-[250px]">
        <canvas bind:this={scoreChartCanvas}></canvas>
      </div>
    </div>

    <div class="lg:col-span-1 space-y-6">
      
      <div class="bg-gray-800/80 p-6 rounded-2xl border border-gray-700 shadow-xl relative overflow-hidden">
        <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-gray-400 to-transparent opacity-20"></div>
        <h3 class="text-gray-400 text-[10px] font-bold uppercase tracking-wider mb-4 border-b border-gray-700 pb-2">Protocol Mix</h3>
        <div class="h-32 relative">
            <canvas bind:this={protoChartCanvas}></canvas>
            {#if (!data.flow_data?.protocols || data.flow_data.protocols.length === 0)}
              <div class="absolute inset-0 flex items-center justify-center pointer-events-none">
                <span class="text-xs text-gray-600 italic">No Data</span>
              </div>
            {:else}
              <div class="absolute inset-0 flex flex-col items-center justify-center pointer-events-none">
                  <span class="text-2xl font-bold text-white font-mono">{data.flow_data.protocols.length}</span>
                  <span class="text-[10px] text-gray-500 uppercase">Types</span>
              </div>
            {/if}
        </div>
      </div>

      <div class="bg-gray-800/80 p-6 rounded-2xl border border-gray-700 shadow-xl flex-grow relative overflow-hidden">
        <div class="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-gray-400 to-transparent opacity-20"></div>
        <div class="flex justify-between items-center mb-4 border-b border-gray-700 pb-2">
            <h3 class="text-gray-400 text-[10px] font-bold uppercase tracking-wider">Top Source IPs</h3>
            <span class="text-[10px] text-gray-500">By Vol</span>
        </div>
        
        <div class="space-y-4">
            {#if (!data.flow_data?.top_ips || data.flow_data.top_ips.length === 0)}
                <div class="flex flex-col items-center justify-center h-32 text-gray-600">
                    <p class="text-xs italic">Waiting for flows...</p>
                </div>
            {:else}
                {#each data.flow_data.top_ips as ip}
                    <div>
                        <div class="flex justify-between items-center text-xs mb-1">
                            <span class="text-gray-300 font-mono tracking-wide">{ip.label}</span>
                            <span class="text-gray-500 font-mono">{ip.value.toFixed(0)} B/s</span>
                        </div>
                        <div class="w-full h-1.5 bg-gray-700/50 rounded-full overflow-hidden">
                            <div class="h-full bg-gradient-to-r from-blue-600 to-blue-400 rounded-full shadow-[0_0_8px_rgba(59,130,246,0.5)]" 
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
