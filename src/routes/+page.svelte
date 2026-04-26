<script>
	import Game from '$lib/Game.svelte';
</script>

<svelte:head>
	<title>Kingdom Quest</title>
	<meta name="description" content="A colorful 2D platformer adventure. Help Quadra restore the light!">
	<style>
		/* TRUE FULLSCREEN: zero margin, no scroll, hardware-accelerated */
		*, *::before, *::after { box-sizing: border-box; }
		html, body {
			margin: 0; padding: 0;
			width: 100%; height: 100%;
			overflow: hidden;
			background: #000;
			/* Prevent text selection during gameplay */
			user-select: none;
			-webkit-user-select: none;
		}
	</style>
</svelte:head>

<Game width="100vw" height="100vh" />
