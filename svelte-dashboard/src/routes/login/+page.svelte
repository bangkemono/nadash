<script lang="ts">
    import { enhance, applyAction } from '$app/forms';
    import { goto } from '$app/navigation';
    
    export let form; 

    const handleLogin = () => {
        return async ({ result }) => {
            if (result.type === 'success' && result.data?.token) {
                localStorage.setItem('auth_token', result.data.token);
                await goto('/');
            } else if (result.type === 'failure') {
                // turns out you need this line to update the form prop
                await applyAction(result); 
            }
        };
    };
</script>

<div class="flex min-h-screen justify-center items-center bg-gray-900">
    <div class="flex flex-col justify-center bg-gray-800 w-96 p-8 rounded-2xl shadow-2xl border border-gray-700 space-y-6">

        <div class="flex justify-center">
            <div class="p-3 bg-blue-500/10 rounded-full border border-blue-500/20 shadow-[0_0_15px_rgba(59,130,246,0.5)]">
                <!-- MINTOL AI SEK wkwkwk (how do you even draw vectors manually bruh) -->
                <svg class="h-12 w-12 text-blue-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 2l9 4.9V17.1L12 22 3 17.1V6.9L12 2z" />
                    <circle cx="12" cy="12" r="3" class="fill-blue-400/20 stroke-blue-400" />
                    <path stroke-linecap="round" stroke-linejoin="round" d="M12 2v4 M12 22v-4" class="opacity-50" />
                </svg>
            </div>
        </div>

        <div class="text-center space-y-2">
            <h1 class="text-3xl font-bold text-white tracking-tight">Sign In</h1>
            <p class="text-gray-400 text-sm">please sign in beforehand</p>
        </div>

        <form method="POST" use:enhance={handleLogin} class="w-full space-y-4">
            {#if form?.error}
                <div class="p-3 bg-red-500/20 border border-red-500/50 rounded-lg text-red-200 text-xs text-center">
                    {form.error}
                </div>
            {/if}
            <div class="flex h-10 w-full bg-gray-700/50 rounded-lg border border-gray-600">
                <input class="flex-1 p-2 text-white" type="text" id="username" name="username" placeholder="Enter your username">
            </div>
            <div class="flex h-10 w-full bg-gray-700/50 rounded-lg border border-gray-600">
              <input class="flex-1 p-2 text-white" type="password" id="password" name="password" placeholder="Enter your password">
            </div>
            <button class="w-full h-10 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-lg transition-colors shadow-lg shadow-blue-600/20">
                Sign In
            </button>
        </form>

        <div class="p-3">
            <p class="text-gray-400 text-sm opacity-50" data-sveltekit-preload-data="tap">&copy; 2026 isrlab. All Rights Reserved.</p>
        </div>

    </div>
</div>
