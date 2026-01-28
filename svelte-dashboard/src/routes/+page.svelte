<script lang="ts">
    import { fly } from 'svelte/transition';
    import { onMount } from 'svelte';
    import { goto } from '$app/navigation';
    import Chart from 'chart.js/auto';
    import SidebarItem from './sidebarItem.svelte'; 

    export let data;
    let active = true;
    let lightMode = false; 
    let isTraining = false;
    let isOffline = true;
    let maxFlowBytes = 1;
    let scoreChartCanvas: HTMLCanvasElement;
    let protoChartCanvas: HTMLCanvasElement;
    let scoreChart: Chart;
    let protoChart: Chart;

    $: user = data.user;
    let dashboard = {
        status: "OFFLINE",
        score: 0.0,
        alert: "System Normal",
        timestamp: "---",
        interface: "---",
        model: "---",
        metrics: { cpu: 0, mbps: 0, pps: 0 },
        flow_data: { top_ips: [], protocols: [] },
        history: []
    };

    $: sidebarWidthClass = active ? 'w-64' : 'w-20';
    $: themeBg = lightMode ? 'bg-white text-slate-900' : 'bg-[#030712] text-white';
    $: sidebarBg = lightMode ? 'bg-slate-100 border-slate-400' : 'bg-gray-800 border-gray-700';
    $: cardClass = lightMode ? 'bg-slate-100 border-slate-400 shadow-sm' : 'bg-gray-800/50 border-gray-700 shadow-xl backdrop-blur-sm';
    
    $: displayScore = (dashboard.score * 100).toFixed(0);
    $: scoreBarWidth = (dashboard.score * 100);
    $: isCritical = dashboard.score > 0.75; 
    $: statusColor = isCritical ? 'bg-red-500' : (isOffline ? 'bg-gray-500' : 'bg-emerald-500'); 

    async function fetchData() {
        const token = localStorage.getItem('auth_token');
        if (!token) return goto('/login');
        try {
            const res = await fetch('api/dashboard', {
                headers: { 'Authorization': `Bearer ${token}` }
            });
            if (res.status === 401) return goto('/login'); 
            const json = await res.json();
            if (json && json.timestamp) {
                const previousHistory = dashboard.history || [];
                dashboard = json; 
                isOffline = false;
                const newPoint = { time: dashboard.timestamp, score: dashboard.score }; 
                dashboard.history = [...previousHistory, newPoint].slice(-60); 
                updateCharts();
            }
        } catch (e) { 
            isOffline = true;
            dashboard.status = "OFFLINE"; 
        }
    }

    function initCharts() {
        if (!scoreChartCanvas || !protoChartCanvas) return;
        const ctx = scoreChartCanvas.getContext('2d');
        const gradient = ctx.createLinearGradient(0, 0, 0, 400); 
        gradient.addColorStop(0, 'rgba(59, 130, 246, 0.4)');
        gradient.addColorStop(1, 'rgba(59, 130, 246, 0.0)'); 

        scoreChart = new Chart(scoreChartCanvas, {
            type: 'line',
            data: { labels: [], datasets: [{ data: [], backgroundColor: gradient, borderColor: '#3b82f6', fill: true, tension: 0.4, pointRadius: 0 }] },
            options: {
                responsive: true,
                maintainAspectRatio: false, 
                animation: { duration: 0 },
                plugins: { legend: { display: false } },
                scales: {
                    x: { grid: { display: false }, ticks: { font: { size: 10 }, maxTicksLimit: 6 } },
                    y: { beginAtZero: true, max: 1.0 } 
                }
            }
        });

        protoChart = new Chart(protoChartCanvas, {
            type: 'doughnut',
            data: { labels: [], datasets: [{ data: [], backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#94a3b8'], borderWidth: 0 }] },
            options: { responsive: true, maintainAspectRatio: false, cutout: '80%' } 
        });
    }

    function updateCharts() {
        if (!scoreChart || !protoChart) return;
        scoreChart.data.labels = dashboard.history.map(d => d.time); 
        scoreChart.data.datasets[0].data = dashboard.history.map(d => d.score); 
        scoreChart.data.datasets[0].borderColor = isCritical ? '#EF4444' : '#60A5FA';
        scoreChart.update('none');

        const protocols = dashboard.flow_data?.protocols || [];
        if (protocols.length > 0) {
            protoChart.data.labels = protocols.map(p => p.label); 
            protoChart.data.datasets[0].data = protocols.map(p => p.value);
            protoChart.update();
        }

        const topIps = dashboard.flow_data?.top_ips || []; 
        if (topIps.length > 0) {
            maxFlowBytes = Math.max(...topIps.map(ip => ip.value)) || 1; 
        }
    }

    async function retrainModel() {
        if (isTraining) return;
        isTraining = true;
        const token = localStorage.getItem('auth_token');
        try {
            const res = await fetch('/api/train/retrain-recent', { 
                method: 'POST',
                headers: { 'Authorization': `Bearer ${token}` }
            });
            const result = await res.json(); 
            alert(`AI Sync: ${result.message}`);
        } catch (e) { alert("Failed to retrain"); }
        finally { isTraining = false; }
    }

    onMount(() => {
        initCharts();
        fetchData();
        const interval = setInterval(fetchData, 2000); // 2-second heartbeat 
        return () => clearInterval(interval);
    });
</script>

<div class="min-h-screen flex overflow-hidden transition-colors duration-500 {themeBg}">
    <aside class="h-screen border-r transition-all duration-300 {sidebarWidthClass} {sidebarBg} flex flex-col">
        <div class="h-20 border-b flex items-center w-full {lightMode ? 'border-slate-400' : 'border-gray-700'} {active ? 'px-6' : 'justify-center'}">
            <button on:click={() => active = !active} class="text-blue-500 hover:rotate-12 transition-transform flex-shrink-0">
                <svg class="h-10 w-10" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                    <path d="M12 2l9 4.9V17.1L12 22 3 17.1V6.9L12 2z" />
                    <circle cx="12" cy="12" r="3" class="fill-blue-400/20 stroke-blue-400" />
                </svg>
            </button>
            {#if active}
                <div transition:fly={{ x: -10 }} class="ml-4 flex flex-col">
                    <span class="font-bold tracking-tight text-lg leading-none">NADASH</span>
                    <div class="flex items-center gap-1 mt-1">
                        <span class="text-[9px] bg-blue-500/10 text-blue-500 px-1 rounded font-black uppercase tracking-tighter leading-none">{dashboard.interface}</span>
                        <span class="text-[9px] text-gray-500 font-mono leading-none">{dashboard.model}</span>
                    </div>
                </div>
            {/if}
        </div>

        <nav class="flex-grow py-6">
            <ul class="flex flex-col gap-4">
                <SidebarItem {active} {lightMode} label="Dashboard" path="/">
                    <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 12l9-9 9 9M5 10v10a1 1 0 001 1h3m10-11l2 2m-2-2v10a1 1 0 01-1 1h-3m-6 0a1 1 0 001-1v-4a1 1 0 011-1h2a1 1 0 011 1v4a1 1 0 001 1m-6 0h6" /></svg>
                </SidebarItem>
                <SidebarItem {active} {lightMode} label="Analytics" path="/">
                    <svg class="h-6 w-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" /></svg>
                </SidebarItem>
            </ul>
        </nav>

        <div class="px-4 mb-4">
            <button on:click={() => lightMode = !lightMode} class="w-full flex items-center gap-3 p-2 rounded-lg transition-colors {lightMode ? 'hover:bg-slate-200 text-slate-600' : 'hover:bg-gray-700 text-gray-400'}">
                <div class="w-10 h-10 flex-shrink-0 flex items-center justify-center">
                    {#if lightMode}
                        <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path d="M17.293 13.293A8 8 0 016.707 2.707a8.001 8.001 0 1010.586 10.586z"/></svg>
                    {:else}
                        <svg class="w-5 h-5" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 2a1 1 0 011 1v1a1 1 0 11-2 0V3a1 1 0 011-1zm4 8a4 4 0 11-8 0 4 4 0 018 0zm-.464 4.95l.707.707a1 1 0 001.414-1.414l-.707-.707a1 1 0 00-1.414 1.414zm2.12-10.607a1 1 0 010 1.414l-.706.707a1 1 0 11-1.414-1.414l.707-.707a1 1 0 011.414 0zM17 11a1 1 0 100-2h-1a1 1 0 100 2h1zm-7 4a1 1 0 011 1v1a1 1 0 11-2 0v-1a1 1 0 011-1z" clip-rule="evenodd"/></svg>
                    {/if}
                </div>
                {#if active} <span class="text-[10px] font-black uppercase tracking-widest">{lightMode ? 'Dark' : 'Light'} Mode</span> {/if}
            </button>
        </div>

        <div class="border-t py-6 flex flex-col gap-6 {lightMode ? 'border-slate-400' : 'border-gray-700'} {active ? 'px-6' : 'items-center'}">
            <div class="flex items-center w-full {active ? '' : 'justify-center'}">
                <div class="h-10 w-10 rounded-full bg-blue-600 flex items-center justify-center font-bold text-white flex-shrink-0 uppercase shadow-lg shadow-blue-500/20">{user?.name?.charAt(0) || 'U'}</div>
                {#if active} 
                    <div transition:fly={{ x: -10 }} class="ml-4 truncate">
                        <p class="text-[10px] text-gray-500 uppercase font-black leading-none mb-1">Identity</p>
                        <p class="text-sm font-bold truncate leading-none uppercase">{user?.name || 'User'}</p>
                    </div>
                {/if}
            </div>
            <form action="/logout" method="POST" class="w-full">
                <button class="flex items-center justify-center bg-red-500/10 hover:bg-red-500/20 text-red-400 border border-red-500/30 transition-all {active ? 'w-full py-2.5 rounded-lg' : 'h-12 w-12 mx-auto rounded-xl'}">
                    <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M17 16l4-4m0 0l-4-4m4 4H7m6 4v1a3 3 0 01-3 3H6a3 3 0 01-3-3V7a3 3 0 013-3h4a3 3 0 013 3v1"/></svg>
                </button>
            </form>
        </div>
    </aside>

    <main class="flex-grow overflow-y-auto p-8 relative">
        <header class="flex justify-between items-start mb-10 relative z-10">
            <div>
                <h1 class="text-3xl font-bold uppercase tracking-tight">System Node</h1>
                <div class="flex items-center gap-3 mt-1">
                    <div class="h-2 w-2 rounded-full {statusColor} {isCritical ? 'animate-ping' : ''}"></div>
                    <p class="text-xs font-mono tracking-widest uppercase {lightMode ? 'text-slate-500' : 'text-gray-500'}">
                        {dashboard.status} // <span class="text-blue-500 font-bold">{dashboard.interface}</span>
                    </p>
                </div>
            </div>
            <button on:click={retrainModel} disabled={isTraining} class="px-4 py-2 text-[10px] font-black uppercase tracking-widest border border-gray-700 hover:bg-red-500/10 hover:border-red-500/50 transition-all">
                {isTraining ? 'Reporting...' : 'False Positive?'}
            </button>
        </header>

        {#if dashboard.alert && dashboard.alert !== "System Normal"}
            <div transition:fly={{ y: -20 }} class="mb-8 px-6 py-3 bg-red-500/10 border border-red-500/50 rounded-xl flex items-center gap-4 animate-pulse shadow-[0_0_20px_rgba(239,68,68,0.2)]">
                <span class="text-red-500 font-black text-lg">⚠️</span>
                <span class="text-red-400 font-bold text-sm uppercase tracking-wider">{dashboard.alert}</span>
            </div>
        {/if}

        <div class="grid grid-cols-1 lg:grid-cols-4 gap-6 relative z-10">
            <div class="p-6 rounded-2xl border {cardClass} relative overflow-hidden">
                <div class="absolute top-0 left-0 w-1 h-full {isCritical ? 'bg-red-500 shadow-[0_0_10px_rgba(239,68,68,0.5)]' : 'bg-blue-500 shadow-[0_0_10px_rgba(59,130,246,0.3)]'}"></div>
                <h3 class="text-[10px] font-bold uppercase mb-4 tracking-widest {lightMode ? 'text-slate-400' : 'text-gray-500'}">Anomaly Probability</h3>
                <div class="text-5xl font-black font-mono tracking-tighter">{displayScore}%</div>
                <div class="mt-6 h-1 w-full bg-slate-100/50 rounded-full overflow-hidden">
                    <div class="h-full {isCritical ? 'bg-red-500' : 'bg-blue-500'} transition-all duration-700" style="width: {scoreBarWidth}%"></div>
                </div>
            </div>

            <div class="lg:col-span-2 p-6 rounded-2xl border {cardClass} h-[320px]">
                <h3 class="text-xs font-bold uppercase mb-4 tracking-widest {lightMode ? 'text-slate-400' : 'text-gray-500'}">Threat Analysis</h3>
                <div class="h-[240px]">
                    <canvas bind:this={scoreChartCanvas}></canvas>
                </div>
            </div>
            
            <div class="lg:col-span-1 grid grid-cols-1 gap-4">
                <div class="p-4 rounded-xl border {cardClass} flex justify-between items-center">
                    <p class="text-[10px] font-bold uppercase {lightMode ? 'text-slate-400' : 'text-gray-500'}">CPU Load</p>
                    <p class="text-xl font-bold font-mono tracking-tighter">{dashboard.metrics.cpu}%</p>
                </div>
                <div class="p-4 rounded-xl border {cardClass} flex justify-between items-center">
                    <p class="text-[10px] font-bold uppercase {lightMode ? 'text-slate-400' : 'text-gray-500'}">PKT/SEC</p>
                    <p class="text-xl font-bold font-mono tracking-tighter text-emerald-600">{dashboard.metrics.pps}</p>
                </div>
                <div class="p-4 rounded-xl border {cardClass} flex justify-between items-center">
                    <p class="text-[10px] font-bold uppercase {lightMode ? 'text-slate-400' : 'text-gray-500'}">Throughput</p>
                    <p class="text-xl font-bold font-mono tracking-tighter text-blue-600">{dashboard.metrics.mbps} <span class="text-xs text-slate-500">MB/S</span></p>
                </div>
            </div>

            <div class="lg:col-span-3 p-6 rounded-2xl border {cardClass}">
                <h3 class="text-[10px] font-bold uppercase mb-6 tracking-widest {lightMode ? 'text-slate-400' : 'text-gray-500'}">Top IP Flows</h3>
                <div class="grid grid-cols-1 md:grid-cols-2 gap-x-12 gap-y-6">
                    {#each dashboard.flow_data.top_ips as ip}
                        <div class="space-y-2">
                            <div class="flex justify-between text-[10px] font-mono">
                                <span class="{lightMode ? 'text-slate-600' : 'text-gray-400'}">{ip.label}</span>
                                <span class="text-blue-600 font-bold">{(ip.value / 1024).toFixed(1)} KB/S</span>
                            </div>
                            <div class="w-full h-1 {lightMode ? 'bg-slate-100' : 'bg-gray-700'} rounded-full overflow-hidden">
                                <div class="h-full bg-blue-500 shadow-[0_0_8px_rgba(59,130,246,0.3)]" style="width: {(ip.value / maxFlowBytes) * 100}%"></div>
                            </div>
                        </div>
                    {/each}
                </div>
            </div>

            <div class="lg:col-span-1 p-6 rounded-2xl border {cardClass}">
                <h3 class="text-[10px] font-bold uppercase mb-4 {lightMode ? 'text-slate-400' : 'text-gray-500'} tracking-widest text-center">Protocol Mix</h3>
                <div class="h-44 relative">
                    <canvas bind:this={protoChartCanvas}></canvas>
                </div>
            </div>
        </div>
    </main>
</div>
