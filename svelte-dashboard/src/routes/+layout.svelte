<script lang="ts">
	import './layout.css';
	import favicon from '$lib/assets/favicon.svg';
    import '@fontsource/jetbrains-mono';
    import '@fontsource/space-grotesk';

	let { children } = $props();
</script>

<svelte:head><link rel="icon" href={favicon} /></svelte:head>
{@render children()}
