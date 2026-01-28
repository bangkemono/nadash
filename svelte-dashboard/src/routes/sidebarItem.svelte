<script lang="ts">
    import { fly } from 'svelte/transition';
    export let active: boolean;
    export let label: string;
    export let path: string = "#";
    export let lightMode: boolean;
</script>

<li class="w-full group cursor-pointer transition-colors {lightMode ? 'text-slate-500 hover:text-blue-600' : 'text-slate-400 hover:text-blue-400'}">
    <a href={path} class="flex items-center w-full h-full {active ? 'px-6' : 'justify-center'} py-2">
        <div class="w-10 h-10 flex-shrink-0 rounded-xl flex items-center justify-center transition-all border border-transparent 
            {lightMode ? 'bg-slate-200 group-hover:bg-blue-50 group-hover:border-blue-100' : 'bg-gray-700/50 group-hover:bg-gray-700 group-hover:border-gray-600'}">
            <slot />
        </div>
        {#if active} 
            <span transition:fly={{ x: -5 }} class="ml-4 font-semibold whitespace-nowrap">
                {label}
            </span> 
        {/if}
    </a>
</li>
