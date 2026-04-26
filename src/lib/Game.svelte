<script>
	import { onMount } from 'svelte';

	let { width = '100vw', height = '100vh' } = $props();
	
	// STATE MACHINE: PRE_START -> INTRO -> MENU -> PLAY
	let appState = $state('PRE_START'); 
	let transitionActive = $state(false);
	let isHoveringStart = $state(false);

	// WEB AUDIO API SCHEDULING (PERFECT CROSSFADE)
	let audioContext = null;
	let audioBuffer = null;
	let globalGain = null;
	let isMuted = $state(false);
	let nextStartTime = -1;
	let schedulingInterval;
	const CROSSFADE_TIME = 2.0;

	async function initPerfectAudio() {
		if (audioContext) {
			if (audioContext.state === 'suspended') audioContext.resume();
			return;
		}
		try {
			const AudioContextClass = window.AudioContext || window.webkitAudioContext;
			audioContext = new AudioContextClass();
			
			globalGain = audioContext.createGain();
			globalGain.connect(audioContext.destination);
			globalGain.gain.value = isMuted ? 0 : 1; 

			// Fetch exact binary
			const response = await fetch('/audio/menu-theme.mp3');
			const arrayBuffer = await response.arrayBuffer();
			audioBuffer = await audioContext.decodeAudioData(arrayBuffer);

			nextStartTime = audioContext.currentTime; 
			
			// Schedule first node and lookahead
			scheduleNextNode();
			schedulingInterval = setInterval(() => {
				if (audioBuffer && nextStartTime !== -1 && nextStartTime < audioContext.currentTime + 3.0) {
					scheduleNextNode();
				}
			}, 1000);
		} catch (err) {
			console.error("Web Audio API failed", err);
		}
	}

	function scheduleNextNode() {
		if (!audioBuffer || !audioContext) return;
		
		const source = audioContext.createBufferSource();
		source.buffer = audioBuffer;
		
		const localGain = audioContext.createGain();
		source.connect(localGain);
		localGain.connect(globalGain);
		
		const dur = audioBuffer.duration;
		const fade = CROSSFADE_TIME;
		const startTime = nextStartTime;
		
		source.start(startTime);
		// Fade IN
		localGain.gain.setValueAtTime(0, startTime);
		localGain.gain.linearRampToValueAtTime(0.8, startTime + fade);
		
		// Fade OUT
		const fadeOutStart = startTime + dur - fade;
		localGain.gain.setValueAtTime(0.8, fadeOutStart);
		localGain.gain.linearRampToValueAtTime(0, startTime + dur);
		
		source.stop(startTime + dur);
		nextStartTime = fadeOutStart;
	}

	function toggleMute(e) {
		if(e) e.stopPropagation();
		isMuted = !isMuted;
		if (globalGain && audioContext) {
			globalGain.gain.setTargetAtTime(isMuted ? 0 : 1, audioContext.currentTime, 0.05);
		}
	}

	function fadeOutMusic() {
		if (globalGain && audioContext) {
			globalGain.gain.setTargetAtTime(0, audioContext.currentTime, 0.4); 
		}
	}

	function playClick() {
		try {
			const clickSound = document.getElementById('click-audio');
			if (clickSound) {
				clickSound.volume = 0.6; // Weicherer Klick-Sound
				clickSound.currentTime = 0;
				clickSound.play().catch(e => console.log('SFX block', e));
			}
		} catch(e) {}
	}

	// TRIGGER THE CINEMATIC EXPERIENCE
	function startIntro() {
		if (appState !== 'PRE_START') return;

		// 1. Play immediate click SFX (Preloaded, Full Volume)
		playClick();

		// 2. Init synchronous background orchestrator
		initPerfectAudio();

		// 3. Start pure CSS camera fly
		appState = 'INTRO';

		// Trigger intro-to-menu drop after camera pan ends
		setTimeout(() => {
			appState = 'MENU';
		}, 4800);
	}

	function startGame(e) {
		e.stopPropagation();
		transitionActive = true;
		fadeOutMusic();

		const rect = e.target.getBoundingClientRect();
		fireConfetti(rect.left + rect.width / 2, rect.top + rect.height / 2);

		setTimeout(() => {
			appState = 'PLAY';
			transitionActive = false;
			particles = [];
		}, 2000);
	}

	// MOUSE TRACKING
	let windowWidth = $state(1000);
	let windowHeight = $state(800);
	let mouseX = $state(0);
	let mouseY = $state(0);

	function handleMouseMove(e) {
		if (appState !== 'MENU') return;
		mouseX = (e.clientX / windowWidth) * 2 - 1;
		mouseY = (e.clientY / windowHeight) * 2 - 1;
	}

	// CONFETTI STARS & FLOWERS
	let particles = $state([]);
	function fireConfetti(cx, cy) {
		const symbols = ['⭐', '🌟', '🌸', '🌼', '🍄', '💦', '🎵'];
		let temp = [];
		for (let i = 0; i < 70; i++) {
			const angle = Math.random() * Math.PI * 2;
			const speed = 15 + Math.random() * 40;
			temp.push({
				id: i,
				x: cx,
				y: cy,
				vx: Math.cos(angle) * speed,
				vy: Math.sin(angle) * speed - 15,
				size: 20 + Math.random() * 40,
				symbol: symbols[Math.floor(Math.random() * symbols.length)],
				rotation: Math.random() * 360,
				rotationSpeed: (Math.random() - 0.5) * 60,
				life: 1.0,
			});
		}
		particles = temp;
		requestAnimationFrame(animateConfetti);
	}

	function animateConfetti() {
		let hasAlive = false;
		particles = particles.map(p => {
			p.vy += 1.5; // Gravity pull down
			p.x += p.vx;
			p.y += p.vy;
			p.rotation += p.rotationSpeed;
			p.life -= 0.012; 
			if (p.life > 0) hasAlive = true;
			return p;
		});

		if (hasAlive && transitionActive) {
			requestAnimationFrame(animateConfetti);
		}
	}

	const titleChars = Array.from("KINGDOM QUEST");

	// MAGIC DUST
	let dust = [];
	for (let i = 0; i < 40; i++) {
		dust.push({
			id: i,
			left: Math.random() * 250, 
			duration: 8 + Math.random() * 15,
			delay: Math.random() * 10,
			size: 2 + Math.random() * 5
		});
	}
</script>

<svelte:window 
	on:mousemove={handleMouseMove} 
	bind:innerWidth={windowWidth}
	bind:innerHeight={windowHeight} />

<svelte:head>
	<link href="https://fonts.googleapis.com/css2?family=Lilita+One&display=swap" rel="stylesheet">
</svelte:head>

<div class="game-viewport bloom-scene" style="width: {width}; height: {height};">
	<div class="texture-overlay"></div>

	<!-- PRELOAD CLICK SOUND FOR INSTANT ZERO-LATENCY PLAYBACK -->
	<audio id="click-audio" src="/audio/mixkit-select-click-1109.wav" preload="auto"></audio>

	<!-- BACKGROUND VISUALS (Persistent layer, transitions smoothly) -->
	{#if appState !== 'PLAY'}
		<div class="parallax-container 
			{appState === 'PRE_START' ? 'pan-static' : ''} 
			{appState === 'INTRO' ? 'pan-active' : ''} 
			{appState === 'MENU' ? 'pan-ended' : ''}">
			
			<div class="layer sky"></div>

			<div class="layer magic-dust">
				{#each dust as d}
					<div class="dust-mote" style="
						left: {d.left}vw; 
						width: {d.size}px; height: {d.size}px;
						animation-duration: {d.duration}s;
						animation-delay: -{d.delay}s;
					"></div>
				{/each}
			</div>

			<div class="layer clouds">
				<div class="cloud" style="top: 10vh; left: 20vw; transform: scale(3);"></div>
				<div class="cloud" style="top: 25vh; left: 80vw; transform: scale(1.5);"></div>
				<div class="cloud" style="top: 15vh; left: 140vw; transform: scale(4);"></div>
				<div class="cloud" style="top: 20vh; left: 200vw; transform: scale(2);"></div>
			</div>

			<!-- INTRO SPECIFIC PROPS -->
			{#if appState === 'PRE_START' || appState === 'INTRO'}
				<div class="layer intro-props">
					<div class="giant-flower">🌻</div>
					<div class="intro-quadra cameo-flip">
						<div class="eyes">
							<div class="eye"><div class="pupil"></div></div>
							<div class="eye"><div class="pupil"></div></div>
						</div>
					</div>
				</div>
			{/if}

			<!-- CASTLES -->
			<div class="layer castles">
				<div class="tower" style="left: 170vw; height: 50vh; transform: scale(1.2);">
					<div class="tower-roof"></div><div class="tower-base"></div>
				</div>
			</div>

			<!-- WOBBLY CONTINUOUS HILLS -->
			<div class="layer hills">
				<div class="hill-continuous hill-bg"></div>
				<div class="hill-continuous hill-mg"></div>
				<div class="hill-continuous hill-fg"></div>
			</div>
		</div>
	{/if}

	<!-- STATE UI LOGIC -->

	{#if appState === 'PRE_START'}
		<!-- 1. PRE-START OVERLAY (Invisible but catches clicks) -->
		<!-- It shows the animated mouse and pulsing text directly over the bright wonder world! -->
		<div class="pre-start-overlay" role="button" tabindex="0" onclick={startIntro} onkeydown={(e) => { if (e.key === 'Enter') startIntro(); }}>
			<div class="mouse-icon"><div class="mouse-wheel"></div></div>
			<p class="splash-pulse">CLICK TO ENTER THE KINGDOM</p>
		</div>

	{:else if appState === 'MENU'}

		<!-- 3. MENU (Buttons, Title, Logic ready) -->
		<div class="menu-screen {transitionActive ? 'fade-away' : ''}">
			<!-- HUGE EXTRUDED 3D TITLE -->
			<h1 class="extruded-title">
				{#each titleChars as char, i}
					<span class="char-drop" style="animation-delay: {i * 0.08}s">
						{char === ' ' ? '\u00A0' : char}
					</span>
				{/each}
			</h1>

			<!-- MENU UI CONTAINER (fades in) -->
			<div class="menu-ui-fade-in">
				<!-- HERO CUBIE -->
				<div class="cubie {isHoveringStart ? 'jumping-happily' : 'idle'} {transitionActive ? 'rocket-fly' : ''}">
					<div class="eyes">
						<div class="eye"><div class="pupil" style="transform: translate({mouseX * 6}px, {mouseY * 6}px)"></div></div>
						<div class="eye"><div class="pupil" style="transform: translate({mouseX * 6}px, {mouseY * 6}px)"></div></div>
					</div>
				</div>

				<!-- MENUS -->
				<div class="buttons-cluster {transitionActive ? 'disappear' : ''}">
					<button 
						class="wonder-btn main-btn" 
						onmouseover={() => isHoveringStart = true}
						onmouseout={() => isHoveringStart = false}
						onmousedown={playClick}
						onclick={startGame}
					>
						START GAME
					</button>
					<div class="sub-buttons">
						<button class="wonder-btn small-btn" onmousedown={playClick}>⚙ OPTIONS</button>
						<button class="wonder-btn small-btn" onmousedown={playClick}>CREDITS</button>
						<button class="wonder-btn small-btn mute-btn" onmousedown={playClick} onclick={toggleMute} aria-label="Toggle mute" title="Mute Audio">
							{isMuted ? '🔈' : '🔊'}
						</button>
					</div>
				</div>
			</div>
		</div>

		<!-- MENU -> PLAY TRANSFORMATION OVERLAYS -->
		{#if transitionActive}
			<div class="particles">
				{#each particles as p (p.id)}
					{#if p.life > 0}
						<div class="particle-emoji" 
							style="
								left: {p.x}px; top: {p.y}px; 
								font-size: {p.size}px; 
								transform: translate(-50%, -50%) rotate({p.rotation}deg); 
								opacity: {p.life};
								filter: drop-shadow(0 5px 10px rgba(0,0,0,0.4));
							">
							{p.symbol}
						</div>
					{/if}
				{/each}
			</div>
		{/if}

	{:else if appState === 'PLAY'}

		<!-- 4. PLAY PHASE -->
		<div class="game-world">
			<h2>LEVEL 1: WONDER PLAINS</h2>
			<div class="platformer-view">[ PLACEHOLDER ]<br/>Das eigentliche Spiel-Level wird hier später implementiert.</div>
		</div>

	{/if}

	<div class="white-flash {transitionActive && !particles.length ? 'flash-active' : ''}"></div>
</div>

<style>
	/* MAIN VIEWPORT */
	.game-viewport {
		position: relative; overflow: hidden; background: #000;
		font-family: 'Lilita One', sans-serif; user-select: none;
	}

	.bloom-scene {
		filter: drop-shadow(0 0 10px rgba(255,255,255,0.1)) saturate(1.1);
	}
	.texture-overlay {
		position: absolute; inset: 0; z-index: 999; pointer-events: none;
		background-image: radial-gradient(rgba(0,0,0,0.15) 1px, transparent 1px);
		background-size: 5px 5px; 
		mix-blend-mode: overlay; opacity: 0.8;
	}

	.layer { position: absolute; top: 0; left: 0; width: 100%; height: 100vh; pointer-events: none; }

	/* --- PRE-START OVERLAY UI --- */
	.pre-start-overlay {
		position: absolute; inset: 0; z-index: 100;
		display: flex; flex-direction: column; justify-content: center; align-items: center;
		background: rgba(0,0,0,0.2) radial-gradient(circle, transparent 50%, rgba(0,0,0,0.4));
		cursor: pointer;
	}
	
	/* Animated Mouse Icon */
	.mouse-icon {
		width: 32px; height: 50px; border: 3px solid #fff; border-radius: 20px;
		position: relative; margin-bottom: 25px; box-shadow: 0 5px 15px rgba(0,0,0,0.5);
	}
	.mouse-wheel {
		width: 4px; height: 12px; background: #fff; border-radius: 2px;
		position: absolute; top: 8px; left: 50%; transform: translateX(-50%);
		animation: scrollWheel 1.5s infinite;
	}
	@keyframes scrollWheel {
		0% { top: 8px; opacity: 1; }
		100% { top: 25px; opacity: 0; }
	}

	.splash-pulse {
		font-size: 2.5vw; color: #fff; text-shadow: 0 4px 10px rgba(0,0,0,0.8);
		animation: blinker 1.5s infinite ease-in-out; margin: 0; letter-spacing: 2px;
	}
	@keyframes blinker { 50% { opacity: 0.3; } }


	/* --- INTRO PAN --- */
	.parallax-container {
		position: absolute;
		top: 0; left: 0;
		width: 250vw; /* Extremely wide */
		height: 100vh;
	}
	.pan-static {
		transform: translateX(0); /* Frame 0 resting state */
	}
	.pan-active {
		animation: cinematicPan 4.8s cubic-bezier(0.3, 0, 0.2, 1) forwards;
	}
	.pan-ended {
		transform: translateX(-150vw);
	}
	@keyframes cinematicPan {
		0% { transform: translateX(0); }
		100% { transform: translateX(-150vw); }
	}

	/* SCENERY SETTINGS */
	.sky { background: linear-gradient(180deg, #74b9ff 0%, #a29bfe 60%, #dfe6e9 100%); width: 250vw; }
	
	.dust-mote {
		position: absolute; background: #fff; border-radius: 50%;
		bottom: -10vh; opacity: 0;
		box-shadow: 0 0 10px 4px rgba(255, 234, 167, 0.8);
		animation: floatUp linear infinite;
	}
	@keyframes floatUp {
		0% { transform: translateY(0) scale(1); opacity: 0; }
		20% { opacity: 0.8; }
		80% { opacity: 0.8; }
		100% { transform: translateY(-120vh) scale(0.5); opacity: 0; }
	}

	.cloud {
		position: absolute; width: 120px; height: 50px; background: #fff; border-radius: 50px;
		box-shadow: 0 10px 20px rgba(0,0,0,0.05), inset 0 -5px 15px rgba(0,0,0,0.05);
	}
	.cloud::before, .cloud::after {
		content: ''; position: absolute; background: #fff; border-radius: 50%;
	}
	.cloud::before { width: 60px; height: 60px; top: -30px; left: 15px; }
	.cloud::after { width: 40px; height: 40px; top: -20px; right: 20px; }

	.hill-continuous {
		position: absolute; border-radius: 50% 50% 0 0; transform-origin: bottom center;
		width: 300vw; 
	}
	.hill-bg {
		height: 50vh; left: -25vw; bottom: -5vh;
		background: linear-gradient(135deg, #0984e3, #74b9ff);
	}
	.hill-mg {
		height: 40vh; left: -25vw; bottom: -5vh;
		background: linear-gradient(135deg, #55efc4, #00b894);
		box-shadow: 0 0 40px rgba(0,0,0,0.1);
	}
	.hill-fg {
		height: 35vh; left: -25vw; bottom: -10vh;
		background: linear-gradient(135deg, #ffeaa7, #fdcb6e);
		border-top: 20px solid #00b894;
		box-shadow: 0 -10px 30px rgba(0,0,0,0.2);
	}

	.tower { position: absolute; bottom: 5vh; width: 80px; }
	.tower-base {
		width: 100%; height: 100%; border-radius: 10px 10px 0 0;
		background: linear-gradient(135deg, #ffeaa7, #fab1a0);
		box-shadow: inset -10px 0 20px rgba(0,0,0,0.1);
	}
	.tower-roof {
		position: absolute; top: -40px; left: -10px; width: 100px; height: 50px;
		background: #e17055; clip-path: polygon(50% 0%, 100% 100%, 0% 100%);
	}

	.giant-flower {
		position: absolute; left: 80vw; bottom: 25vh; font-size: 15rem;
		transform-origin: bottom; animation: sway 3s infinite alternate ease-in-out;
	}
	@keyframes sway {
		0% { transform: rotate(-5deg); filter: hue-rotate(0); }
		100% { transform: rotate(5deg); filter: hue-rotate(15deg); }
	}
	
	.intro-quadra {
		position: absolute; left: 110vw; bottom: 30vh;
		width: 80px; height: 80px;
		background: radial-gradient(circle at 35% 35%, #ff7675, #d63031);
		border-radius: 40% 40% 45% 45%; 
		box-shadow: 0 15px 25px rgba(214, 48, 49, 0.5), inset -8px -12px 20px rgba(0,0,0,0.3);
		display: flex; justify-content: center; align-items: center; padding-top: 10px;
	}
	.cameo-flip { animation: flipOver 2s cubic-bezier(0.4, 0, 0.2, 1) 1.5s forwards; }
	@keyframes flipOver {
		0% { transform: translateY(0) rotate(0); }
		50% { transform: translateY(-30vh) rotate(180deg); }
		100% { transform: translateY(0) rotate(360deg); }
	}

	/* --- MENU SCREEN --- */
	.menu-screen {
		position: absolute; inset: 0; z-index: 10;
		display: flex; flex-direction: column; align-items: center;
		padding-top: 10vh; gap: 6vh;
	}

	.menu-ui-fade-in {
		opacity: 0; padding-top: 4vh; display: flex; flex-direction: column; align-items: center; gap: 8vh;
		animation: majesticDrop 1.5s ease-out 0.8s forwards;
	}

	.extruded-title {
		margin: 0; font-size: 7vw;
		color: #fceabb;
		text-shadow: 
			0 1px 0 #f8b500, 0 2px 0 #f8b500, 0 3px 0 #f8b500, 0 4px 0 #f8b500,
			0 5px 0 #d99a00, 0 6px 0 #d99a00, 0 7px 0 #d99a00,
			0 8px 0 #b37e00, 0 9px 0 #b37e00,
			0 10px 0 #8c6300,
			0 12px 10px rgba(0,0,0,0.4), 0 25px 30px rgba(0,0,0,0.2);
	}
	.char-drop {
		display: inline-block; opacity: 0; transform: translateY(-300px);
		animation: majesticDrop 1.2s cubic-bezier(0.175, 0.885, 0.32, 1.275) forwards;
	}
	@keyframes majesticDrop {
		0% { opacity: 0; transform: translateY(-50px); }
		100% { opacity: 1; transform: translateY(0); }
	}

	/* CUBIE */
	.cubie {
		position: relative; width: 100px; height: 100px;
		background: radial-gradient(circle at 35% 35%, #ff7675, #d63031);
		border-radius: 40% 40% 45% 45%; 
		box-shadow: 0 15px 25px rgba(214, 48, 49, 0.5), inset -8px -12px 20px rgba(0,0,0,0.3);
		display: flex; justify-content: center; align-items: center; padding-top: 10px;
	}
	.eyes { display: flex; gap: 16px; }
	.eye {
		width: 22px; height: 32px; background: #fff; border-radius: 50%;
		position: relative; overflow: hidden; box-shadow: inset 0 3px 8px rgba(0,0,0,0.2);
	}
	.pupil {
		width: 12px; height: 14px; background: #2d3436; border-radius: 50%;
		position: absolute; top: 50%; left: 50%; margin: -7px 0 0 -6px;
	}

	.idle { animation: cubieFloat 4s ease-in-out infinite; }
	.jumping-happily { animation: cubieHappy 0.6s ease-in-out infinite; }
	.rocket-fly { animation: flyToStarts 1s cubic-bezier(0.4, 0, 0.2, 1) forwards !important; }

	@keyframes cubieFloat {
		0%, 100% { transform: translateY(0); }
		50% { transform: translateY(-10px); }
	}
	@keyframes cubieHappy {
		0%, 100% { transform: scale(1, 1) translateY(0); }
		30% { transform: scale(1.15, 0.85) translateY(10px); }
		50% { transform: scale(0.9, 1.15) translateY(-30px); }
		70% { transform: scale(1.05, 0.95) translateY(0); }
	}
	@keyframes flyToStarts {
		0% { transform: scale(1, 1) translateY(0); }
		100% { transform: scale(0.5, 2) translateY(-100vh) rotate(720deg); opacity: 0; }
	}

	/* BUTTONS */
	.buttons-cluster {
		display: flex; flex-direction: column; align-items: center; gap: 20px;
	}
	.wonder-btn {
		font-family: inherit; color: #fff; border: none; cursor: pointer;
		text-shadow: 2px 2px 0 #d63031; border-radius: 50px;
		transition: all 0.1s cubic-bezier(0.175, 0.885, 0.32, 1.275);
	}
	.main-btn {
		font-size: 32px; padding: 20px 80px;
		background: linear-gradient(to bottom, #ff9ff3, #f368e0); border: 6px solid #fff;
		box-shadow: 0 12px 0 #b33939, 0 20px 30px rgba(0,0,0,0.5);
	}
	.main-btn:hover {
		transform: scale(1.1) translateY(-8px); box-shadow: 0 20px 0 #b33939, 0 30px 40px rgba(0,0,0,0.6);
	}
	.main-btn:active {
		transform: scale(0.95) translateY(5px); box-shadow: 0 5px 0 #b33939, 0 10px 15px rgba(0,0,0,0.4);
	}

	.sub-buttons { display: flex; gap: 20px; align-items: center; }
	.small-btn {
		font-size: 16px; padding: 12px 30px;
		background: #00cec9; border: 4px solid #fff; text-shadow: 1px 1px 0 #01908c;
		box-shadow: 0 6px 0 #01908c, 0 10px 15px rgba(0,0,0,0.3);
	}
	.small-btn:hover {
		transform: scale(1.05) translateY(-4px); box-shadow: 0 10px 0 #01908c, 0 15px 20px rgba(0,0,0,0.4);
	}
	.small-btn:active {
		transform: scale(0.95) translateY(2px); box-shadow: 0 4px 0 #01908c, 0 5px 10px rgba(0,0,0,0.3);
	}
	.mute-btn { padding: 12px 20px; border-radius: 50%; font-size: 18px; line-height: 1; text-shadow: none; }

	/* CONFETTI LAYER & TRANSITION */
	.particles { position: absolute; inset: 0; z-index: 20; pointer-events: none; }
	.particle-emoji { position: absolute; }
	.fade-away { animation: fadeAway 1.5s forwards; }
	.disappear { opacity: 0; pointer-events: none; }
	
	.white-flash {
		position: absolute; inset: 0; background: #fff; z-index: 1000;
		pointer-events: none; opacity: 0; filter: blur(20px);
	}
	.flash-active { animation: flashWipe 1.5s ease-in forwards; }

	@keyframes fadeAway {
		0% { opacity: 1; filter: brightness(1); }
		100% { opacity: 0; filter: brightness(2); }
	}
	@keyframes flashWipe {
		0% { opacity: 0; }
		80% { opacity: 1; background: #fff; filter: blur(0); }
		100% { opacity: 1; background: #000; filter: blur(0); }
	}

	.game-world {
		position: absolute; inset: 0; background: #55efc4; z-index: 50; display: flex; flex-direction: column;
		align-items: center; justify-content: center; color: #2d3436;
	}
	.platformer-view { font-size: 2rem; margin-top: 20px; }

</style>
