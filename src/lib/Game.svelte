<script>
	import { onMount } from 'svelte';
	import { fade, scale } from 'svelte/transition';

	let { width = '100vw', height = '100vh' } = $props();
	
	// STATE MACHINE: PRE_START -> INTRO -> MENU -> TRANSITION_FLOWER -> STORY -> CREDITS -> LOADING -> LEVEL_SELECT -> PLAY
	let appState = $state('PRE_START'); 
	let transitionActive = $state(false);
	let isHoveringStart = $state(false);
	let isCreditsOpen = $state(false);
	let isSettingsOpen = $state(false);
	let panFinished = $state(false);
	let isWinking = $state(false);

	// SETTINGS STATES
	let musicVolume = $state(0.4);
	let isSFXEnabled = $state(true);
	let typingSpeedMode = $state('normal'); // slow, normal, fast

	// ============================================================
	// STORY CONFIG — TIMESTAMPS (adjust to your story-voice.mp3!)
	// Set startTime/endTime to the exact seconds in the audio file
	// where each box's narration begins and ends.
	// Run `console.log(storyVoice.currentTime)` in the browser
	// console while playing to find the right values.
	// ============================================================
	const storyConfig = [
		{
			text: "Once, the kingdom shined in endless colors. The light of the crystals brought joy and life to every living soul.",
			startTime: 0,     
			endTime: 7.3625,     
			scene: "meadow"
		},
		{
			text: "But a dark, nameless power has stolen the radiance, shroudding the world in grey shadows. all lives seems frozen...",
			startTime: 7.5,
			endTime: 14.8,
			scene: "grey"
		},
		{
			text: "Quadra, you are the only one who can break the darkness. Journey through the forgotten lands, find the lost fragments, and bring back the light!",
			startTime: 15.0,
			endTime: 24.2,
			scene: "hope"
		},
		{
			text: "The adventure begins... now.",
			startTime: 24.5,
			endTime: 28.0,
			scene: "dawn"
		}
	];
	let currentStoryBox = $state(0);
	let displayedStoryText = $state("");
	let storyInterval;
	let storyTimeupdateHandler = null;
	let isBlockFinished = $state(false);

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

	function toggleMute() {
		isMuted = !isMuted;
		updateVolume();
	}

	function updateVolume() {
		// Dips volume when in Settings or Credits for better focus
		const reduction = (isSettingsOpen || appState === 'CREDITS') ? 0.4 : 1.0;
		const finalVolume = isMuted ? 0 : musicVolume * reduction;

		// ENFORCE: The Menu Theme (Web Audio) must be SILENT if we are in Game States
		const isMenuState = (appState === 'PRE_START' || appState === 'INTRO' || appState === 'MENU' || appState === 'CREDITS');
		
		if (globalGain && audioContext) {
			const targetWebAudioVol = isMenuState ? finalVolume : 0;
			globalGain.gain.setTargetAtTime(targetWebAudioVol, audioContext.currentTime, 0.1);
		}
		
		const mapMusic = document.getElementById('map-theme-audio');
		if (mapMusic) mapMusic.volume = finalVolume;
	}

	$effect(() => {
		// This effect tracks musicVolume, isMuted, isSettingsOpen, and appState
		updateVolume();
	});

	function fadeOutMusic() {
		if (schedulingInterval) {
			clearInterval(schedulingInterval);
			schedulingInterval = null;
		}
		nextStartTime = -1; // Stop scheduling new nodes
		
		if (globalGain && audioContext) {
			// Fast but smooth fade to absolute zero
			globalGain.gain.setTargetAtTime(0, audioContext.currentTime, 0.2); 
		}
	}

	function playClick() {
		if (!isSFXEnabled) return;
		try {
			const clickSound = document.getElementById('click-audio');
			if (clickSound) {
				clickSound.volume = 0.6 * musicVolume; // Scale with music for consistency or keep separate
				clickSound.currentTime = 0;
				clickSound.play().catch(e => console.log('SFX block', e));
			}
		} catch(e) {}
	}

	// TRIGGER THE CINEMATIC EXPERIENCE
	function startIntro() {
		if (appState !== 'PRE_START') return;

		// No click sound here to keep the pan absolutely calm and cinematic!

		// 2. Init synchronous background orchestrator
		initPerfectAudio();

		// 3. Start pure CSS camera fly
		appState = 'INTRO';

		// Trigger intro-to-menu drop after camera pan ends
		setTimeout(() => {
			appState = 'MENU';
			panFinished = true; // Triggers the high-fidelity 'Pop' effects
		}, 4800);
	}

	function startGame(e) {
		if (e && e.stopPropagation) e.stopPropagation();
		transitionActive = true;
		
		// 1. Stop Menu Theme IMMEDIATELY
		fadeOutMusic();

		// 2. Fire Confetti
		if (e && e.target) {
			const rect = e.target.getBoundingClientRect();
			fireConfetti(rect.left + rect.width / 2, rect.top + rect.height / 2);
		}

		// 3. Sequential state changes
		setTimeout(() => {
			appState = 'TRANSITION_FLOWER';
			
			// GIVE THE TRANSITION (MOMENT OF SILENCE) 5 SECONDS
			setTimeout(() => {
				appState = 'STORY';
				transitionActive = false;
				particles = [];
				currentStoryBox = 0;
				
				// 4. START MAP THEME NOW (After the transition silence)
				const mapMusic = document.getElementById('map-theme-audio');
				if (mapMusic) {
					mapMusic.currentTime = 0;
					mapMusic.volume = musicVolume;
					mapMusic.play().catch(() => {});
				}
				
				startTypewriter();
			}, 5000); 
		}, 800);
	}

	// ── AUDIO CLEANUP (Ghost Music Prevention) ──
	$effect(() => {
		return () => {
			if (audioCtx) {
				try { audioCtx.close(); } catch(e) {}
			}
			const audios = document.querySelectorAll('audio');
			audios.forEach(a => {
				try {
					a.pause();
					a.src = ""; // Force stop
					a.load();
					a.remove();
				} catch(e) {}
			});
		};
	});

	function startTypewriter() {
		if (storyInterval) clearInterval(storyInterval);
		isBlockFinished = false;
		displayedStoryText = "";
		let i = 0;
		const currentBox = storyConfig[currentStoryBox];
		const currentText = currentBox.text;
		const storyVoice = document.getElementById('story-voice-audio');
		let triggered = false;

		const triggerBlockFinished = () => {
			if (triggered) return;
			triggered = true;
			isBlockFinished = true;
			// Unducking: Restore music volume for whichever track is currently active
			const activeMusicId = (currentStoryBox === 1) ? 'demon-theme-audio' : 'map-theme-audio';
			fadeAudio(activeMusicId, 0.6, 600);
		};

		// 1. NARRATION LOGIC (Only if timestamps are defined)
		if (storyVoice && currentBox.startTime !== undefined && currentBox.endTime !== undefined) {
			// Clean up previous listeners
			if (storyTimeupdateHandler) {
				storyVoice.removeEventListener('timeupdate', storyTimeupdateHandler);
			}
			
			storyVoice.playbackRate = (currentStoryBox === 0) ? 0.95 : 1.0;
			storyVoice.currentTime = currentBox.startTime;
			
			// Ducking: Lower music while speaking
			fadeAudio('map-theme-audio', 0.2, 400);

			storyVoice.play().catch(() => {});

			// Precise stop logic
			storyTimeupdateHandler = () => {
				if (storyVoice.currentTime >= currentBox.endTime) {
					storyVoice.pause();
					storyVoice.removeEventListener('timeupdate', storyTimeupdateHandler);
					storyTimeupdateHandler = null;
					triggerBlockFinished();
				}
			};
			storyVoice.addEventListener('timeupdate', storyTimeupdateHandler);
			
			// 1a. MUSIC SWITCHING LOGIC (Wonder-style Scene Audio)
			if (currentStoryBox === 1) { // Box 2 (The Decay / Demon King)
				fadeAudio('map-theme-audio', 0, 500);
				setTimeout(() => {
					const demonMusic = document.getElementById('demon-theme-audio');
					if (demonMusic) {
						demonMusic.currentTime = 20; // Start at 20th second as requested
						demonMusic.volume = 0;
						demonMusic.play().catch(() => {});
						fadeAudio('demon-theme-audio', 0.2, 500); // 0.2 because of ducking
					}
				}, 500);
			} else if (currentStoryBox === 2) { // Box 3 (The Hope / Hero return)
				fadeAudio('demon-theme-audio', 0, 500);
				setTimeout(() => {
					fadeAudio('map-theme-audio', 0.2, 500); // 0.2 because of ducking
				}, 500);
			}

			// Safety timeout
			const duration = (currentBox.endTime - currentBox.startTime) / storyVoice.playbackRate;
			setTimeout(() => {
				storyVoice.pause();
				triggerBlockFinished();
			}, (duration + 1) * 1000);
		}

		// 2. TYPEWRITER SPEED CALCULATION
		let typingSpeed = 40;
		if (currentBox.startTime !== undefined && currentBox.endTime !== undefined && storyVoice) {
			const durMs = ((currentBox.endTime - currentBox.startTime) / storyVoice.playbackRate) * 1000;
			typingSpeed = Math.max(20, Math.floor(durMs / currentText.length));
		}

		// 3. TYPEWRITER EXECUTION
		storyInterval = setInterval(() => {
			if (i < currentText.length) {
				displayedStoryText += currentText.charAt(i);
				i++;
			} else {
				clearInterval(storyInterval);
				// If no audio is driving the 'finished' state, trigger it after typing
				if (currentBox.startTime === undefined) {
					setTimeout(triggerBlockFinished, 500);
				}
			}
		}, typingSpeed);
	}

	function nextStoryBox() {
		if (!isBlockFinished) return;
		playClick();
		
		if (currentStoryBox < storyConfig.length - 1) {
			currentStoryBox++;
			startTypewriter();
		} else {
			finishStory();
		}
	}

	function fadeAudio(id, targetVolume, duration = 500) {
		const el = document.getElementById(id);
		if (!el) return;
		
		if (targetVolume > 0 && el.paused) {
			el.volume = 0;
			el.play().catch(e => {});
		}

		let currentVol = el.volume;
		const steps = 10;
		const stepAmt = (targetVolume - currentVol) / steps;
		let i = 0;
		
		const interval = setInterval(() => {
			i++;
			currentVol += stepAmt;
			el.volume = Math.max(0, Math.min(1, currentVol));
			if (i >= steps) {
				clearInterval(interval);
				el.volume = targetVolume;
				if (targetVolume === 0) el.pause();
			}
		}, duration / steps);
	}



	function finishStory() {
		if (storyInterval) clearInterval(storyInterval);
		// Clean up any active timeupdate handler
		const storyVoice = document.getElementById('story-voice-audio');
		if (storyVoice) {
			if (storyTimeupdateHandler) {
				storyVoice.removeEventListener('timeupdate', storyTimeupdateHandler);
				storyTimeupdateHandler = null;
			}
			storyVoice.pause();
		}
		// POST-INTRO: raise map theme permanently to 60%
		fadeAudio('map-theme-audio', 0.6, 1000);

		appState = 'LOADING';
		setTimeout(() => {
			appState = 'LEVEL_SELECT';
		}, 2500);
	}

	function startLevel1() {
		try {
			const mapTheme = document.getElementById('map-theme-audio');
			if (mapTheme) {
				let vol = mapTheme.volume;
				let fade = setInterval(() => {
					vol -= 0.05;
					if (vol <= 0) {
						clearInterval(fade);
						mapTheme.pause();
					} else {
						mapTheme.volume = vol;
					}
				}, 100);
			}
		} catch(err) {}
		
		appState = 'PLAY';
	}

	// MOUSE TRACKING
	let windowWidth = $state(1000);
	let windowHeight = $state(800);
	let mouseX = $state(0);
	let mouseY = $state(0);

	function handleMouseMove(e) {
		if (appState !== 'MENU' && appState !== 'LEVEL_SELECT') return;
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

<div class="game-viewport bloom-scene {appState === 'TRANSITION_FLOWER' || appState === 'STORY' ? 'flower-bloom-active' : ''} {isSettingsOpen ? 'game-paused' : ''}" style="width: {width}; height: {height};">
	<div class="texture-overlay"></div>

	<!-- PRELOAD SOUNDS FOR INSTANT ZERO-LATENCY PLAYBACK -->
	<audio id="click-audio" src="/audio/mixkit-select-click-1109.wav" preload="auto"></audio>
	<audio id="click-effect-audio" src="/audio/click-effect.mp3" preload="auto"></audio>
	<audio id="story-voice-audio" src="/story-voice.mp3" preload="auto"></audio>
	<audio id="map-theme-audio" src="/audio/map-theme.mp3" loop preload="auto"></audio>
	<audio id="demon-theme-audio" src="/audio/1-the-demon-king.mp3" loop preload="auto"></audio>

	<!-- BACKGROUND VISUALS (Persistent layer, transitions smoothly) -->
	{#if appState !== 'PLAY' && appState !== 'LEVEL_SELECT' && appState !== 'LOADING'}
		<div class="parallax-container 
			{appState === 'PRE_START' ? 'pan-static' : ''} 
			{appState === 'INTRO' ? 'pan-active' : ''} 
			{appState === 'MENU' ? 'pan-ended' : ''}
			{appState === 'TRANSITION_FLOWER' || appState === 'STORY' ? 'pan-flower-bloom' : ''}">
			
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
				<div class="wonder-sun-happy menu-sun"></div>
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

	{:else if appState === 'MENU' || appState === 'TRANSITION_FLOWER'}

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
						<button class="wonder-btn small-btn" onmousedown={playClick} onclick={() => isSettingsOpen = true}>⚙ SETTINGS</button>
						<button class="wonder-btn small-btn" onmousedown={playClick} onclick={() => appState = 'CREDITS'}>CREDITS</button>
						<button class="wonder-btn small-btn mute-btn" onmousedown={playClick} onclick={toggleMute} aria-label="Toggle mute" title="Mute Audio">
							{isMuted ? '🔈' : '🔊'}
						</button>
					</div>
				</div>
			</div>
		</div>

		<!-- MENU -> TRANSITION FLOWER OVERLAYS -->
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

	{:else if appState === 'STORY'}

		<!-- STORY OVERLAY: CINEMATIC VFX BACKGROUNDS -->
		<div class="story-overlay story-scene-{storyConfig[currentStoryBox]?.scene ?? 'meadow'}"
			 in:fade={{ duration: 800 }}
			 onclick={nextStoryBox}>

			<!-- ═══ SCENE 1: PARADISE SUNRISE ═══
			     God-Rays + Floating Petal Particles -->
			{#if storyConfig[currentStoryBox]?.scene === 'meadow'}
				<div class="scene-bg scene-meadow">
					<!-- Majestic Kingdom Backdrop -->
					<div class="kingdom-backdrop">
						<div class="wonder-sun-happy"></div>
					</div>
					<!-- Animated sunrise gradient overlay -->
					<div class="sunrise-overlay"></div>
					<!-- God-rays: 7 conic beams from top-center -->
					<div class="god-rays">
						{#each Array(7) as _, r}
							<div class="god-ray" style="--r:{r}; animation-delay: {r * 0.4}s"></div>
						{/each}
					</div>
					<!-- Floating petal particles -->
					<div class="petal-layer">
						{#each dust.slice(0, 20) as d}
							<div class="petal" style="
								left: {d.left * 0.4}vw;
								animation-duration: {d.duration * 0.8}s;
								animation-delay: -{d.delay * 0.5}s;
								font-size: {10 + d.size * 3}px;
							">🌸</div>
						{/each}
					</div>
					<!-- Glowing sun orb -->
					<div class="vfx-sun"></div>
				</div>
			{/if}

			<!-- ═══ SCENE 2: THE DECAY ═══
			     Grayscale Fade + Ash Particles + Demon King -->
			{#if storyConfig[currentStoryBox]?.scene === 'grey'}
				<div class="scene-bg scene-grey {isBlockFinished ? '' : 'shaking'}">
					<!-- NEW: Demon King Silhouette looming in background -->
					<div class="demon-king-shadow">
						<div class="demon-eye-glow"></div>
					</div>
					<!-- Desaturation overlay that animates from color to B&W -->
					<div class="grey-desaturate"></div>
					<!-- Fog layers -->
					<div class="fog fog-1"></div>
					<div class="fog fog-2"></div>
					<div class="fog fog-3"></div>
					<!-- Falling ash particles -->
					<div class="ash-layer">
						{#each dust.slice(0, 25) as d}
							<div class="ash-particle" style="
								left: {d.left * 0.4}vw;
								width: {d.size * 1.5}px;
								height: {d.size * 1.5}px;
								animation-duration: {d.duration * 0.7}s;
								animation-delay: -{d.delay * 0.4}s;
								opacity: {0.3 + Math.random() * 0.5};
							"></div>
						{/each}
					</div>
				</div>
			{/if}

			<!-- ═══ SCENE 3: THE SPOTLIGHT (Cosmic Silence) ═══ -->
			{#if storyConfig[currentStoryBox]?.scene === 'hope'}
				<div class="scene-bg scene-spotlight">
					<div class="cosmos-shimmer"></div>
					<div class="central-spotlight"></div>
					<div class="golden-dust">
						{#each Array(15) as _, i}
							<div class="gold-particle" style="--delay:{i*0.3}s; --x:{Math.random()*100}%; --y:{Math.random()*100}%"></div>
						{/each}
					</div>
					<div class="spotlight-center-container">
						{#key currentStoryBox}
							<div class="hero-quadra">
								<div class="cubie divine-float">
									<div class="eyes"><div class="eye"><div class="pupil"></div></div><div class="eye"><div class="pupil"></div></div></div>
								</div>
							</div>
						{/key}
					</div>
				</div>
			{/if}

			<!-- ═══ SCENE 4: THE GOLDEN HORIZON (The Liberation) ═══ -->
			{#if storyConfig[currentStoryBox]?.scene === 'dawn'}
				<div class="scene-bg scene-hero">
					<div class="victory-flash-overlay"></div>
					<!-- Hill Silhouettes for Depth -->
					<div class="golden-hills">
						<div class="hill-layer hill-far"></div>
						<div class="hill-layer hill-mid"></div>
						<div class="hill-layer hill-near"></div>
						<div class="valley-fog"></div>
					</div>
					<!-- Wonder Energy Sparks -->
					<div class="wonder-energy-layer">
						{#each Array(20) as _, i}
							<div class="energy-spark" style="--delay:{i*0.2}s; --x:{Math.random()*100}%"></div>
						{/each}
					</div>
					<div class="spotlight-center-container">
						{#key currentStoryBox}
							<div class="hero-quadra hero-jump">
								<div class="cubie hero-cubie salto-anim">
									<div class="eyes"><div class="eye"><div class="pupil"></div></div><div class="eye"><div class="pupil"></div></div></div>
									<div class="hero-trail"></div>
								</div>
							</div>
						{/key}
					</div>
				</div>
			{/if}

			<!-- TEXT BOX (always on top, at bottom of screen) -->
			<div class="rpg-text-box cute-box">
				<p class="story-scene-label">Chapter {currentStoryBox + 1} / {storyConfig.length}</p>
				<p class="story-body">{displayedStoryText}</p>
				{#if isBlockFinished}
					<span class="click-to-continue" in:fade>
						{currentStoryBox < storyConfig.length - 1 ? 'Click for Next ▼' : 'Begin the Quest ▶'}
					</span>
				{/if}
			</div>
		</div>

	{:else if appState === 'CREDITS'}

		<!-- 🎬 CINEMATIC WONDER CREDITS -->
		<div class="credits-overlay" in:fade={{ duration: 600 }} out:fade={{ duration: 400 }}>
			<div class="credits-blur-bg"></div>
			
			<div class="credits-content">
				<div class="rolling-container">
					<div class="credit-section">
						<h3>PROGRAMMING & DESIGN</h3>
						<p>Leonit Begzati and Gemini AI</p>
					</div>
					<div class="credit-section">
						<h3>CLASS / GRADE</h3>
						<p>4BHK</p>
					</div>
					<div class="credit-section">
						<h3>INSTITUTION</h3>
						<p>JO HAK</p>
					</div>
					<div class="credit-section">
						<h3>SPECIAL THANKS</h3>
						<p>To the Wonder Kingdom</p>
						<p>&</p>
						<p>The Mystery of Quadra</p>
					</div>
					<div class="firework-trigger">✨</div>
				</div>

				<!-- MINI QUADRA PERFORMER -->
				<div class="mini-quadra-performer">
					<div class="cubie performer-anim">
						<div class="eyes"><div class="eye"><div class="pupil"></div></div><div class="eye"><div class="pupil"></div></div></div>
					</div>
					<div class="performer-shadow"></div>
				</div>
			</div>

			<!-- WONDER PARTICLES (STARS) -->
			<div class="credits-stars">
				{#each Array(12) as _, i}
					<div class="laughing-star" style="--delay: {i * 1.5}s; --x: {10 + Math.random() * 80}%">⭐</div>
				{/each}
			</div>

			<!-- CLOSE BUTTON (FLOWER/STAR) -->
			<button class="credits-close-btn" onclick={() => appState = 'MENU'} onmousedown={playClick}>
				<span class="btn-icon">🌸</span>
				<span class="btn-text">BACK</span>
			</button>
		</div>

	{/if}

	<!-- ⚙️ SETTINGS OVERLAY (Global) -->
	{#if isSettingsOpen}
		<div class="settings-overlay" in:fade={{ duration: 300 }} out:fade={{ duration: 200 }}>
			<div class="settings-modal" in:scale={{ duration: 400, start: 0.8, easing: cubicOut }}>
				<button class="close-x" onclick={() => isSettingsOpen = false} onmousedown={playClick}>×</button>
				
				<h2 class="settings-title">SETTINGS</h2>

				<div class="settings-groups">
					<!-- MUSIC VOLUME -->
					<div class="setting-item">
						<label>MUSIC VOLUME: {Math.round(musicVolume * 100)}%</label>
						<input type="range" min="0" max="1" step="0.01" bind:value={musicVolume} class="wonder-slider" />
					</div>

					<!-- SFX TOGGLE -->
					<div class="setting-item flex-row">
						<label>SOUND EFFECTS (SFX)</label>
						<button class="toggle-btn {isSFXEnabled ? 'active' : ''}" onclick={() => isSFXEnabled = !isSFXEnabled}>
							{isSFXEnabled ? 'ON' : 'OFF'}
						</button>
					</div>

					<!-- TEXT SPEED -->
					<div class="setting-item">
						<label>TEXT SPEED</label>
						<div class="speed-selector">
							<button class={typingSpeedMode === 'slow' ? 'active' : ''} onclick={() => typingSpeedMode = 'slow'}>SLOW</button>
							<button class={typingSpeedMode === 'normal' ? 'active' : ''} onclick={() => typingSpeedMode = 'normal'}>NORMAL</button>
							<button class={typingSpeedMode === 'fast' ? 'active' : ''} onclick={() => typingSpeedMode = 'fast'}>FAST</button>
						</div>
					</div>
				</div>

				<button class="apply-btn" onclick={() => isSettingsOpen = false} onmousedown={playClick}>APPLY & CLOSE</button>
			</div>
		</div>
	{/if}

	<!-- APP CONTENT -->
	{#if appState === 'LOADING'}

		<!-- KNUFFIGER LOADING SCREEN -->
		<div class="loading-screen kingdom-loading" in:fade={{ duration: 500 }} out:fade={{ duration: 800 }}>
			<div class="loading-meadow"></div>
			<div class="cubie loading-run">
				<div class="eyes">
					<div class="eye"><div class="pupil"></div></div>
					<div class="eye"><div class="pupil"></div></div>
				</div>
			</div>
			<div class="loading-text">Gathering the colors of the kingdom...</div>
		</div>

	{:else if appState === 'LEVEL_SELECT'}

		<!-- BUNTES KÖNIGREICH LEVEL SELECT -->
		<div class="level-select-screen" in:fade={{ duration: 1000 }}>
			
			<div class="kingdom-bg">
				<div class="k-sky"></div>
				<div class="k-sun"></div>
				<div class="k-clouds">
					<div class="k-cloud" style="top: 10%; left: 10%;"></div>
					<div class="k-cloud" style="top: 20%; left: 70%; transform: scale(1.5);"></div>
				</div>
				<div class="k-hills"></div>
				<div class="k-river"></div>
			</div>

			<h2 class="level-select-title">CHOOSE YOUR PATH</h2>
			
			<div class="levels-container">
				<!-- Level 1 (Windmühle) -->
				<button class="k-level-node active-node" style="left: 20%; top: 30%;" onclick={startLevel1} onmousedown={playClick}>
					<div class="node-icon windmill">
						<div class="wm-base"></div>
						<div class="wm-blades"></div>
					</div>
					<div class="node-label">1. WONDER PLAINS</div>
				</button>
				
				<!-- Level 2 (Eisschloss) -->
				<div class="k-level-node locked-node" style="left: 50%; top: 50%;">
					<div class="node-icon ice-castle">
						<div class="ic-tower"></div>
						<div class="ic-tower tall"></div>
						<div class="ic-tower"></div>
					</div>
					<div class="node-label">2. CRYSTAL CAVES</div>
					<div class="lock-icon">🔒</div>
				</div>

				<!-- Level 3 (Vulkan) -->
				<div class="k-level-node locked-node" style="left: 75%; top: 20%;">
					<div class="node-icon volcano">
						<div class="vc-body"></div>
						<div class="vc-lava"></div>
					</div>
					<div class="node-label">3. FORGOTTEN PEAK</div>
					<div class="lock-icon">🔒</div>
				</div>
			</div>
		</div>

	{:else if appState === 'PLAY'}

		<!-- 4. PLAY PHASE -->
		<div class="game-world" in:fade={{ duration: 1000 }}>
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
		width: 300vw; /* Extremely wide to prevent black borders during pan/scale */
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
	.sky { background: linear-gradient(180deg, #74b9ff 0%, #a29bfe 60%, #dfe6e9 100%); width: 300vw; }
	
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
		animation: hillBounce 4s infinite ease-in-out;
	}
	.hill-fg {
		height: 35vh; left: -25vw; bottom: -10vh;
		background: linear-gradient(135deg, #ffeaa7, #fdcb6e);
		border-top: 20px solid #00b894;
		box-shadow: 0 -10px 30px rgba(0,0,0,0.2);
		animation: hillBounce 3s infinite ease-in-out alternate;
	}
	@keyframes hillBounce {
		0%, 100% { transform: scaleY(1); }
		50% { transform: scaleY(1.08) skewX(2deg); }
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
		border-radius: 15px; 
		box-shadow: 0 15px 25px rgba(214, 48, 49, 0.5), inset -8px -12px 20px rgba(0,0,0,0.3);
		display: flex; justify-content: center; align-items: center; padding-top: 10px;
		animation: wonderJump 2s infinite ease-in-out;
	}
	@keyframes wonderJump {
		0% { transform: translateY(0) rotate(0deg) scale(1.2, 0.8); }
		25% { transform: translateY(-100px) rotate(90deg) scale(0.9, 1.1); }
		50% { transform: translateY(-180px) rotate(180deg) scale(1, 1); }
		75% { transform: translateY(-80px) rotate(270deg) scale(0.9, 1.1); }
		100% { transform: translateY(0) rotate(360deg) scale(1.2, 0.8); }
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
		transition: transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
	}
	/* Disable transition when an animation is active to prevent jitter */
	.cubie:is(.idle, .jumping-happily, .salto-anim, .rocket-fly) {
		transition: none !important;
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
		transform: none !important; /* Keep absolutely static as requested */
	}
	.small-btn:hover {
		filter: brightness(1.1);
		box-shadow: 0 6px 0 #01908c, 0 10px 15px rgba(0,0,0,0.3);
	}
	.small-btn:active {
		transform: scale(0.98) !important;
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
	.platformer-view { font-size: 2rem; margin-top: 20px; text-align: center; }

	/* --- NEW PHASES CSS --- */
	.flower-bloom-active {
		animation: worldBloom 5s ease-out forwards;
	}
	@keyframes worldBloom {
		0% { filter: drop-shadow(0 0 10px rgba(255,255,255,0.1)) saturate(1.1); }
		100% { filter: drop-shadow(0 0 40px rgba(255,200,255,0.6)) saturate(1.8) hue-rotate(15deg) brightness(1.2); }
	}

	.pan-flower-bloom {
		/* Glides from the MENU pan-ended state to even further right, very smoothly */
		animation: flowerPan 5s cubic-bezier(0.25, 1, 0.5, 1) forwards;
	}
	@keyframes flowerPan {
		0% { transform: translateX(-150vw); }
		100% { transform: translateX(-180vw) scale(1.1); }
	}

	/* ============================================
	   STORY OVERLAY & CINEMATIC SCENES
	   ============================================ */
	.story-overlay {
		position: absolute; inset: 0; z-index: 60;
		display: flex; flex-direction: column; justify-content: flex-end; align-items: center;
		padding-bottom: 8vh; cursor: pointer; overflow: hidden;
	}
	.scene-bg { position: absolute; inset: 0; pointer-events: none; overflow: hidden; }

	/* SCENE 1: PARADISE SUNRISE — God-Rays + Petals */
	.story-scene-meadow { background: #0a0010; }
	.scene-meadow {
		background: linear-gradient(180deg, #2c1654 0%, #a8520a 35%, #f8b500 60%, #55efc4 100%);
		animation: sunriseShift 8s ease-out forwards;
	}
	@keyframes sunriseShift {
		0% { filter: brightness(0.4) saturate(0.5); }
		100% { filter: brightness(1.1) saturate(1.3); }
	}
	.sunrise-overlay {
		position: absolute; inset: 0;
		background: linear-gradient(180deg, rgba(255,150,50,0.5) 0%, transparent 60%);
		animation: sunriseGlow 6s ease-out infinite alternate;
	}
	@keyframes sunriseGlow { 0% { opacity: 0.3; } 100% { opacity: 0.9; } }
	.god-rays { position: absolute; inset: 0; display: flex; justify-content: center; }
	.god-ray {
		position: absolute; top: -10%; left: 48%; width: 60px; height: 130%;
		background: linear-gradient(180deg, rgba(255,234,167,0.55) 0%, transparent 100%);
		transform-origin: top center;
		transform: translateX(-50%) rotate(calc((var(--r) - 3) * 15deg));
		animation: godRayPulse 4s ease-in-out infinite alternate; filter: blur(8px);
	}
	@keyframes godRayPulse {
		0% { opacity: 0.2; transform: translateX(-50%) rotate(calc((var(--r) - 3) * 15deg)) scaleX(0.8); }
		100% { opacity: 0.8; transform: translateX(-50%) rotate(calc((var(--r) - 3) * 15deg)) scaleX(1.3); }
	}
	.vfx-sun {
		position: absolute; top: 10%; left: 42%; transform: translateX(-50%);
		width: 180px; height: 180px; border-radius: 50%;
		background: radial-gradient(circle, #fff 10%, #ffeaa7 45%, transparent 75%);
		box-shadow: 0 0 130px 70px rgba(255,234,167,0.8), 0 0 280px 130px rgba(255,150,50,0.4);
		animation: sunPulse 3s ease-in-out infinite alternate;
	}
	.petal-layer { position: absolute; inset: 0; }
	.petal { position: absolute; bottom: -5%; animation: petalFloat linear infinite; }
	@keyframes petalFloat {
		0% { transform: translateY(0) rotate(0deg); opacity: 0; }
		10% { opacity: 1; }
		90% { opacity: 0.8; }
		100% { transform: translateY(-110vh) rotate(360deg); opacity: 0; }
	}
	@keyframes sunPulse {
		0% { box-shadow: 0 0 80px 40px rgba(255,234,167,0.6), 0 0 160px 80px rgba(255,150,50,0.3); transform: translateX(-50%) scale(1); }
		100% { box-shadow: 0 0 160px 80px rgba(255,234,167,0.95), 0 0 320px 160px rgba(255,150,50,0.5); transform: translateX(-50%) scale(1.08); }
	}

	/* SCENE 2: THE DECAY — Grayscale + Ash Particles */
	.story-scene-grey { background: #1a1a1a; }
	.scene-grey {
		background: linear-gradient(180deg, #4a6741 0%, #3d4a3e 30%, #2d3436 100%);
		animation: greyDecay 3s ease-out forwards;
	}
	@keyframes greyDecay {
		0% { filter: saturate(1) brightness(1); }
		100% { filter: saturate(0) brightness(0.6); }
	}
	/* THE DEMON KING SILHOUETTE */
	.demon-king-shadow {
		position: absolute; top: 0; left: 50%; transform: translateX(-50%);
		width: 100vw; height: 100vh;
		background: radial-gradient(ellipse at top center, rgba(10,0,0,0.9) 0%, transparent 60%);
		opacity: 0;
		animation: demonLoom 4s ease-out forwards 1s;
	}
	.demon-king-shadow::after {
		content: ''; position: absolute; top: 15%; left: 50%; transform: translateX(-50%);
		width: 40vmin; height: 50vmin;
		background: 
			radial-gradient(circle at 35% 30%, #ff0000 0%, transparent 10%), /* left eye */
			radial-gradient(circle at 65% 30%, #ff0000 0%, transparent 10%), /* right eye */
			radial-gradient(ellipse at center, #050505 0%, #000 50%, transparent 70%); /* head/body */
		filter: blur(12px); opacity: 0.8;
		animation: demonLaugh 0.5s infinite alternate ease-in-out;
	}
	@keyframes demonLaugh {
		0% { transform: translateX(-50%) translateY(0) scale(1); filter: blur(12px) brightness(1); }
		100% { transform: translateX(-50%) translateY(-5px) scale(1.02); filter: blur(10px) brightness(1.5); }
	}
	.demon-eye-glow {
		position: absolute; top: 15%; left: 50%; transform: translateX(-50%);
		width: 40vmin; height: 50vmin; pointer-events: none;
		background: 
			radial-gradient(circle at 35% 30%, rgba(255,0,0,0.4) 0%, transparent 20%),
			radial-gradient(circle at 65% 30%, rgba(255,0,0,0.4) 0%, transparent 20%);
		animation: eyeFlicker 0.2s infinite;
	}
	@keyframes eyeFlicker {
		0%, 100% { opacity: 0.3; }
		50% { opacity: 1; }
	}
	@keyframes screenShake {
		0%, 100% { transform: translate(0,0); }
		25% { transform: translate(-2px, 2px); }
		50% { transform: translate(2px, -2px); }
		75% { transform: translate(-2px, -2px); }
	}
	.scene-grey.shaking {
		animation: greyDecay 3s ease-out forwards, screenShake 0.15s infinite;
	}
	@keyframes demonLoom { 
		0% { opacity: 0; transform: translateX(-50%) scale(0.9) translateY(40px); } 
		100% { opacity: 1; transform: translateX(-50%) scale(1.1) translateY(0); } 
	}
	.grey-desaturate {
		position: absolute; inset: 0;
		background: linear-gradient(180deg, rgba(100,100,100,0) 0%, rgba(30,30,30,0.85) 100%);
		animation: decaySpread 4s ease-out forwards;
	}
	@keyframes decaySpread { 0% { opacity: 0; } 100% { opacity: 1; } }
	.fog {
		position: absolute; width: 200%; height: 50%; border-radius: 50%;
		background: radial-gradient(ellipse at center, rgba(180,180,180,0.5) 0%, transparent 70%);
		filter: blur(20px);
	}
	.fog-1 { bottom: -10%; left: -50%; animation: fogDrift 10s ease-in-out infinite alternate; }
	.fog-2 { bottom: 20%; left: -30%; animation: fogDrift 14s ease-in-out infinite alternate-reverse; opacity: 0.6; }
	.fog-3 { bottom: 40%; left: -40%; animation: fogDrift 18s ease-in-out infinite alternate; opacity: 0.3; }
	@keyframes fogDrift { 0% { transform: translateX(-5%); } 100% { transform: translateX(5%); } }
	.ash-layer { position: absolute; inset: 0; }
	.ash-particle {
		position: absolute; top: -5%; border-radius: 2px; background: rgba(150,150,150,0.8);
		animation: ashFall linear infinite;
	}
	@keyframes ashFall {
		0% { transform: translateY(0) rotate(0deg); opacity: 0; }
		10% { opacity: 1; }
		90% { opacity: 0.6; }
		100% { transform: translateY(110vh) rotate(720deg) translateX(40px); opacity: 0; }
	}

	/* SCENE 3: THE SPOTLIGHT — Divine Space */
	.scene-spotlight { 
		background: #050510;
		overflow: hidden;
		display: flex; align-items: center; justify-content: center;
	}
	.cosmos-shimmer {
		position: absolute; inset: 0;
		background: radial-gradient(circle at 30% 30%, rgba(108, 92, 231, 0.08) 0%, transparent 70%);
		filter: blur(60px);
		animation: mistFloat 20s infinite alternate ease-in-out;
	}
	@keyframes mistFloat {
		from { transform: translate(-2%, -2%) scale(1); }
		to { transform: translate(2%, 2%) scale(1.05); }
	}
	.central-spotlight {
		position: absolute; inset: 0;
		background: radial-gradient(circle at center, rgba(255, 255, 255, 0.12) 0%, transparent 50%);
		z-index: 2;
		filter: blur(20px);
		mask-image: radial-gradient(circle at center, black 10%, transparent 80%);
	}
	.gold-particle {
		position: absolute; width: 3px; height: 3px; background: #fff; border-radius: 50%;
		left: var(--x); top: var(--y); opacity: 0;
		animation: divineSparkle 5s infinite ease-in-out var(--delay);
		box-shadow: 0 0 15px rgba(255,255,255,0.8);
	}

	/* SCENE 4: THE GOLDEN HORIZON — Painterly Golden Hour */
	.scene-hero { 
		background: linear-gradient(180deg, #574b90 0%, #e17055 45%, #f9ca24 100%); 
		overflow: hidden;
	}
	.golden-hills { position: absolute; inset: 0; pointer-events: none; }
	.hill-layer { 
		position: absolute; bottom: -5%; width: 140%; left: -20%; 
		/* Organic hand-drawn hill shapes */
		border-radius: 60% 40% 0 0 / 100% 80% 0 0;
	}
	.hill-far { height: 45vh; background: #c0392b; opacity: 0.25; transform: rotate(-2deg) translateX(5%); }
	.hill-mid { height: 38vh; background: #d35400; opacity: 0.45; transform: rotate(3deg) translateX(-5%); border-radius: 40% 60% 0 0 / 80% 100% 0 0; }
	.hill-near { height: 32vh; background: #f39c12; opacity: 0.7; transform: rotate(-1deg); border-radius: 55% 45% 0 0 / 90% 90% 0 0; }
	
	.valley-fog {
		position: absolute; bottom: 0; width: 100%; height: 15vh;
		background: linear-gradient(to top, rgba(255,255,255,0.15), transparent);
		filter: blur(25px);
		mix-blend-mode: soft-light;
	}

	.energy-spark {
		position: absolute; bottom: -20px; left: var(--x); width: 5px; height: 5px;
		background: #f1c40f; border-radius: 50%; box-shadow: 0 0 12px #f1c40f;
		animation: riseEnergyWobble 6s infinite ease-out var(--delay);
	}
	@keyframes riseEnergyWobble {
		0% { transform: translateY(0) translateX(0) scale(1); opacity: 0; }
		20% { opacity: 0.7; }
		50% { transform: translateY(-50vh) translateX(20px) scale(1.2); }
		100% { transform: translateY(-110vh) translateX(-20px) scale(0.5); opacity: 0; }
	}

	.hero-trail {
		position: absolute; inset: -20px; border-radius: 50%;
		background: radial-gradient(circle, rgba(255,255,255,0.3) 0%, transparent 75%);
		filter: blur(15px); opacity: 0;
		animation: trailPulseHero 0.4s infinite;
	}
	@keyframes trailPulseHero {
		0% { transform: scale(1); opacity: 0.5; }
		100% { transform: scale(1.6); opacity: 0; }
	}
	
	/* DIVINE FLOAT (Box 3 Only) */
	.divine-float {
		animation: divineFloatAnim 6s infinite ease-in-out !important;
	}
	@keyframes divineFloatAnim {
		0%, 100% { transform: translateY(0) scale(1); }
		50% { transform: translateY(-15px) scale(1.05); }
	}

	.victory-flash-overlay {
		position: absolute; inset: 0; background: #fff; z-index: 1000;
		pointer-events: none; opacity: 0;
		animation: victoryFlash 1.5s ease-out forwards;
	}
	@keyframes victoryFlash {
		0% { opacity: 1; }
		100% { opacity: 0; }
	}

	.salto-anim {
		animation: quadraSalto 2.2s cubic-bezier(0.4, 0, 0.2, 1) forwards !important;
	}
	@keyframes quadraSalto {
		0% { transform: translateY(100vh) rotate(0deg) scale(1, 1); opacity: 0; }
		5% { opacity: 1; transform: translateY(100vh) scale(1.3, 0.7); } /* Deep Squash */
		20% { transform: translateY(40vh) scale(0.8, 1.4); } /* Stretch Up */
		45% { transform: translateY(-180px) rotate(180deg) scale(1, 1); } /* Mid-Air */
		75% { transform: translateY(30px) rotate(340deg) scale(1, 1); } 
		85% { transform: translateY(0) rotate(360deg) scale(1.4, 0.6); } /* Landing Squash */
		100% { transform: translateY(0) rotate(360deg) scale(1, 1); opacity: 1; }
	}

	.spotlight-center-container {
		position: absolute; top: 50%; left: 50%; transform: translate(-50%, -50%);
		display: flex; justify-content: center; align-items: center;
		width: 100%; height: 100%; pointer-events: none;
	}

	.spotlight {
		position: absolute; width: 60vmin; height: 60vmin; border-radius: 50%;
		background: radial-gradient(circle, rgba(255,234,167,0.35) 0%, rgba(255,180,50,0.1) 40%, transparent 70%);
		animation: spotlightPulse 2.5s ease-in-out infinite;
		box-shadow: 0 0 80px 40px rgba(255,200,80,0.2);
	}
	@keyframes spotlightPulse {
		0%, 100% { transform: translate(-50%,-50%) scale(1); opacity: 0.7; }
		50% { transform: translate(-50%,-50%) scale(1.35); opacity: 1; }
	}
	.swirl-ring {
		position: absolute; top: 50%; left: 50%; border-radius: 50%;
		border: 2px solid rgba(255,234,167,0.5); animation: swirlExpand 4s ease-out infinite;
	}
	.swirl-1 { width:100px; height:100px; margin:-50px 0 0 -50px; animation-delay:0s; }
	.swirl-2 { width:160px; height:160px; margin:-80px 0 0 -80px; animation-delay:0.8s; }
	.swirl-3 { width:230px; height:230px; margin:-115px 0 0 -115px; animation-delay:1.6s; }
	@keyframes swirlExpand {
		0% { transform: scale(0.5) rotate(0deg); opacity: 0.9; }
		100% { transform: scale(2.8) rotate(180deg); opacity: 0; }
	}
	.hero-quadra {
		position: absolute; display: flex; flex-direction: column; align-items: center;
		z-index: 10;
	}
	/* Unified centering logic */
	.scene-dawn .hero-quadra, .scene-hope .hero-quadra { 
		position: relative; top: auto; left: auto; transform: none; 
	}
	
	.kingdom-backdrop {
		position: absolute; inset: 0;
		background: url('/majestic_kingdom_pixel_art_1777234504807.png') no-repeat center center;
		background-size: cover;
		opacity: 0.9;
		z-index: -1;
		filter: brightness(1.2) contrast(1.1);
	}
	@keyframes rayRotate { from { transform: rotate(0); } to { transform: rotate(360deg); } }
	
	@keyframes winkAnim {
		0%, 100% { transform: scaleY(1); }
		50% { transform: scaleY(0.1); }
	}

	.wonder-sun-happy { display: none; } /* Hide old static image sun */
	.hero-glow {
		position: absolute; width: 140px; height: 140px; border-radius: 50%;
		background: radial-gradient(circle, rgba(255,234,167,0.7) 0%, transparent 70%);
		animation: heroGlowPulse 2s ease-in-out infinite; top: -20px; left: -20px;
	}
	/* HERO SCENE VFX */
	.rainbow-burst {
		position: absolute; inset: 0;
		background: radial-gradient(circle, transparent 20%, rgba(255,0,0,0.1) 40%, rgba(255,255,0,0.1) 60%, rgba(0,255,0,0.1) 80%);
		animation: rainbowPulse 4s infinite;
	}
	@keyframes rainbowPulse {
		0%, 100% { transform: scale(1); opacity: 0.3; }
		50% { transform: scale(1.5); opacity: 0.6; filter: hue-rotate(90deg); }
	}
	.stars-layer { position: absolute; inset: 0; pointer-events: none; }
	.star {
		position: absolute; top: 50%; left: 50%; font-size: 2rem;
		transform: rotate(calc(var(--r) * 24deg)) translateY(-40vh);
		animation: starTwinkle 2s infinite var(--d);
	}
	@keyframes starTwinkle {
		0%, 100% { opacity: 0; transform: rotate(calc(var(--r) * 24deg)) translateY(-40vh) scale(0); }
		50% { opacity: 1; transform: rotate(calc(var(--r) * 24deg)) translateY(-45vh) scale(1.5); }
	}
	.hero-glow-rainbow {
		background: radial-gradient(circle, rgba(255,255,255,0.8) 0%, transparent 70%);
		filter: drop-shadow(0 0 30px #ff00ff) drop-shadow(0 0 60px #00ffff);
	}
	@keyframes heroGlowPulse {
		0%, 100% { transform: scale(1); opacity: 0.6; }
		50% { transform: scale(1.5); opacity: 1; }
	}
	.hero-cubie {
		animation: hopeFloat 3s ease-in-out infinite;
		box-shadow: 0 0 50px 20px rgba(255,234,167,0.7), 0 15px 25px rgba(0,0,0,0.5) !important;
	}
	@keyframes hopeFloat {
		0%, 100% { transform: translateY(0); }
		50% { transform: translateY(-20px); }
	}
	.light-mote {
		position: absolute; border-radius: 50%; background: rgba(255,234,167,0.9);
		box-shadow: 0 0 10px 4px rgba(255,200,80,0.7); animation: floatUp linear infinite;
	}
	@keyframes floatUp {
		0% { transform: translateY(0) scale(1); opacity: 0; }
		15% { opacity: 1; }
		85% { opacity: 0.8; }
		100% { transform: translateY(-80vh) scale(0.3); opacity: 0; }
	}

	/* SCENE 4: THE START — White Flash Burst */
	.story-scene-dawn { background: #0a0010; }
	.scene-dawn { background: #fff; animation: dawnFlash 3s ease-out forwards; }
	@keyframes dawnFlash {
		0% { background: #0a0a2a; filter: brightness(0.4); }
		50% { background: #ffeaa7; filter: brightness(1.3); }
		100% { background: #fff; filter: brightness(2.5); }
	}
	.dawn-core {
		position: absolute; top: 50%; left: 50%; transform: translate(-50%,-50%);
		width: 20vmin; height: 20vmin; border-radius: 50%;
		background: radial-gradient(circle, #fff 0%, rgba(255,234,167,0.9) 40%, transparent 70%);
		box-shadow: 0 0 160px 90px rgba(255,255,255,0.9);
		animation: coreExpand 3s ease-out forwards;
	}
	@keyframes coreExpand {
		0% { transform: translate(-50%,-50%) scale(0); opacity: 1; }
		100% { transform: translate(-50%,-50%) scale(8); opacity: 0; }
	}
	.dawn-ring {
		position: absolute; top: 50%; left: 50%; border-radius: 50%;
		border: 4px solid rgba(255,255,255,0.9); animation: ringExpand 3s ease-out forwards;
	}
	.ring-1 { width:20vmin; height:20vmin; margin:-10vmin; animation-delay:0.3s; }
	.ring-2 { width:20vmin; height:20vmin; margin:-10vmin; animation-delay:0.8s; }
	.ring-3 { width:20vmin; height:20vmin; margin:-10vmin; animation-delay:1.3s; }
	@keyframes ringExpand {
		0% { transform: scale(0); opacity: 1; }
		100% { transform: scale(12); opacity: 0; }
	}

	/* STORY TEXT BOX — base */
	.rpg-text-box { position: relative; z-index: 10; margin-bottom: 8vh; }
	.cute-box {
		width: 65vw; max-width: 900px; min-height: 160px;
		background: rgba(255, 255, 255, 0.92); border: 6px solid #74b9ff;
		border-radius: 28px; padding: 30px 44px 52px 44px;
		box-shadow: 0 20px 50px rgba(0,0,0,0.4), inset 0 0 20px rgba(116,185,255,0.15);
		color: #2d3436; font-family: 'Lilita One', sans-serif; font-size: 1.75rem;
		line-height: 1.65; letter-spacing: 0.4px;
		position: relative; backdrop-filter: blur(12px);
		transition: background 0.5s ease, border-color 0.5s ease, color 0.5s ease;
	}
	/* Dark scenes (grey + hope) get a dark glassmorphism box */
	.story-scene-grey .cute-box,
	.story-scene-hope .cute-box {
		background: rgba(0, 0, 0, 0.5);
		backdrop-filter: blur(15px);
		border-color: rgba(255, 234, 167, 0.4);
		color: #ffeaa7;
		box-shadow: 0 20px 50px rgba(0,0,0,0.7), inset 0 0 20px rgba(255,234,167,0.05);
	}
	.story-scene-grey .story-scene-label { color: #b2bec3; }
	.story-scene-hope .story-scene-label { color: #ffd32a; }
	/* Dawn scene gets warm white */
	.story-scene-dawn .cute-box {
		background: rgba(255, 255, 255, 0.75);
		border-color: rgba(255,200,50,0.8);
		color: #2d1a00;
	}
	.story-body { margin: 0; }
	.story-scene-label {
		font-size: 0.9rem; color: #74b9ff; margin: 0 0 10px 0;
		letter-spacing: 3px; text-transform: uppercase;
	}
	.click-to-continue {
		position: absolute; bottom: 14px; right: 28px;
		font-size: 1.2rem; color: #0984e3;
		animation: pulseContinue 1.2s ease-in-out infinite;
	}
	.story-scene-hope .click-to-continue,
	.story-scene-grey .click-to-continue { color: #ffeaa7; }
	@keyframes pulseContinue { 0%, 100% { opacity: 1; } 50% { opacity: 0.15; } }

	/* LOADING SCREEN */
	.loading-screen {
		position: absolute; inset: 0; z-index: 70;
		background: #2d3436; display: flex; flex-direction: column;
		justify-content: center; align-items: center; gap: 40px;
	}
	.loading-bounce {
		animation: loaderBounce 0.8s infinite alternate cubic-bezier(0.4, 0, 0.2, 1);
		box-shadow: 0 20px 30px rgba(0,0,0,0.5);
	}
	@keyframes loaderBounce {
		0% { transform: translateY(0) scale(1, 1); }
		100% { transform: translateY(-60px) scale(0.9, 1.1); }
	}
	.loading-text {
		color: #fff; font-size: 2rem; letter-spacing: 2px;
		animation: blinker 1.5s infinite ease-in-out;
	}

	/* --- LOADING SCREEN: KINGDOM MEADOW --- */
	.kingdom-loading {
		background: #55efc4; overflow: hidden; position: relative;
		display: flex; flex-direction: column; align-items: center; justify-content: center;
		width: 100vw; height: 100vh;
	}
	.loading-meadow {
		position: absolute; bottom: 0; left: 0; width: 100%; height: 35vh;
		background: #00b894; border-top: 15px solid #00cec9;
	}
	.loading-run {
		animation: runInPlace 0.4s infinite alternate; z-index: 10;
		transform-origin: bottom center; margin-bottom: 5vh;
	}
	@keyframes runInPlace {
		0% { transform: translateY(0) rotate(-5deg); }
		100% { transform: translateY(-30px) rotate(5deg); }
	}

	.loading-text {
		color: #fff; font-size: 2.5rem; letter-spacing: 2px; z-index: 10;
		text-shadow: 0 4px 10px rgba(0,0,0,0.3);
		animation: blinker 1.5s infinite ease-in-out;
	}

	/* --- LEVEL SELECT: KNUFFIGES KÖNIGREICH --- */
	.level-select-screen {
		position: absolute; inset: 0; z-index: 80;
		display: flex; flex-direction: column; align-items: center; justify-content: flex-start;
		background: #74b9ff; overflow: hidden; padding-top: 5vh;
	}
	.kingdom-bg {
		position: absolute; inset: 0; z-index: 1; pointer-events: none;
	}
	.k-sky {
		position: absolute; inset: 0; background: linear-gradient(180deg, #74b9ff 0%, #a29bfe 100%);
	}
	.k-sun {
		position: absolute; top: 10%; right: 15%; width: 120px; height: 120px;
		background: #ffeaa7; border-radius: 50%; box-shadow: 0 0 50px #fdcb6e;
		animation: sunPulse 4s infinite alternate;
	}
	@keyframes sunPulse { 0% { transform: scale(1); } 100% { transform: scale(1.1); } }
	
	.k-cloud {
		position: absolute; width: 150px; height: 50px; background: #fff; border-radius: 50px;
		animation: cloudFloat 20s linear infinite;
	}
	.k-cloud::before { content: ''; position: absolute; width: 70px; height: 70px; background: #fff; border-radius: 50%; top: -30px; left: 20px; }
	.k-cloud::after { content: ''; position: absolute; width: 50px; height: 50px; background: #fff; border-radius: 50%; top: -20px; left: 80px; }
	@keyframes cloudFloat { 0% { transform: translateX(-200px); } 100% { transform: translateX(120vw); } }

	.k-hills {
		position: absolute; bottom: -5vh; left: -10vw; width: 120vw; height: 45vh;
		background: #55efc4; border-radius: 50% 50% 0 0; border-top: 15px solid #00b894;
	}
	.k-river {
		position: absolute; bottom: 0; left: 40%; width: 20%; height: 40vh;
		background: #0984e3; clip-path: polygon(40% 0, 60% 0, 100% 100%, 0 100%);
	}

	.level-select-title {
		position: relative; z-index: 10; font-size: 4rem; color: #fff;
		text-shadow: 0 5px 0 #0984e3, 0 10px 20px rgba(0,0,0,0.3);
		margin-bottom: 50px; 
	}

	.levels-container {
		position: relative; z-index: 10; width: 100%; height: 70vh;
	}
	
	.k-level-node {
		position: absolute; background: none; border: none; cursor: pointer;
		display: flex; flex-direction: column; align-items: center; gap: 15px;
		transition: transform 0.2s cubic-bezier(0.175, 0.885, 0.32, 1.275);
	}
	.k-level-node.active-node:hover { transform: scale(1.15) translateY(-10px); }
	
	.node-label {
		background: #fff; color: #2d3436; padding: 10px 20px; border-radius: 20px;
		font-size: 1.5rem; border: 4px solid #fdcb6e; box-shadow: 0 5px 15px rgba(0,0,0,0.2);
	}

	/* ICONS */
	.node-icon { width: 120px; height: 120px; position: relative; display: flex; justify-content: center; }
	
	.windmill .wm-base {
		position: absolute; bottom: 0; width: 60px; height: 80px;
		background: #e17055; border-radius: 20px 20px 0 0; border: 4px solid #fff;
	}
	.windmill .wm-blades {
		position: absolute; top: 10px; width: 10px; height: 100px;
		background: #fff; transform-origin: center; animation: spinBlade 4s linear infinite;
	}
	.windmill .wm-blades::before {
		content: ''; position: absolute; top: 45px; left: -45px; width: 100px; height: 10px; background: #fff;
	}
	@keyframes spinBlade { 100% { transform: rotate(360deg); } }

	.ice-castle .ic-tower { position: absolute; bottom: 0; background: #74b9ff; width: 30px; height: 60px; border-radius: 10px 10px 0 0; border: 4px solid #fff;}
	.ice-castle .ic-tower:nth-child(1) { left: 10px; }
	.ice-castle .ic-tower.tall { left: 45px; height: 90px; background: #0984e3; z-index: 2;}
	.ice-castle .ic-tower:nth-child(3) { left: 80px; }

	.volcano .vc-body {
		position: absolute; bottom: 0; left: 10px; width: 100px; height: 80px;
		background: #2d3436; clip-path: polygon(30% 0, 70% 0, 100% 100%, 0 100%);
	}
	.volcano .vc-lava {
		position: absolute; top: 0; left: 40px; width: 40px; height: 30px;
		background: #d63031; border-radius: 0 0 20px 20px;
	}

	.locked-node { filter: grayscale(1) opacity(0.8); cursor: not-allowed; }
	.lock-icon { position: absolute; top: -20px; right: -20px; font-size: 2.5rem; filter: drop-shadow(0 2px 5px rgba(0,0,0,0.5)); }

	/* ============================================
	   CREDITS SEQUENZ (WONDER STYLE)
	   ============================================ */
	.credits-overlay {
		position: absolute; inset: 0; z-index: 200;
		display: flex; align-items: center; justify-content: center;
		color: #fff; text-align: center;
	}
	.credits-blur-bg {
		position: absolute; inset: 0;
		background: rgba(44, 22, 84, 0.4);
		backdrop-filter: blur(15px);
		-webkit-backdrop-filter: blur(15px);
	}
	.credits-content {
		position: relative; z-index: 10;
		width: 80%; height: 100%;
		display: flex; flex-direction: column; align-items: center;
		overflow: hidden;
	}
	.rolling-container {
		position: absolute; bottom: -100%;
		display: flex; flex-direction: column; gap: 80px;
		animation: rollCredits 25s linear forwards;
	}
	@keyframes rollCredits {
		0% { bottom: -100%; }
		100% { bottom: 120%; }
	}
	.credit-section h3 {
		font-size: 1.2rem; color: #fdcb6e; letter-spacing: 4px; margin-bottom: 15px;
		text-shadow: 0 4px 10px rgba(0,0,0,0.3);
	}
	.credit-section p {
		font-size: 2.2rem; font-weight: bold; margin: 5px 0;
		filter: drop-shadow(0 5px 15px rgba(0,0,0,0.5));
	}
	.firework-trigger {
		font-size: 3rem; opacity: 0;
		animation: creditFirework 1s ease-out forwards 24.5s;
	}
	@keyframes creditFirework {
		0% { transform: scale(0); opacity: 0; }
		50% { transform: scale(2); opacity: 1; filter: hue-rotate(360deg); }
		100% { transform: scale(3); opacity: 0; filter: blur(20px); }
	}

	/* MINI QUADRA TRICKS */
	.mini-quadra-performer {
		position: absolute; right: 10%; bottom: 15%;
		display: flex; flex-direction: column; align-items: center;
	}
	.performer-anim {
		width: 60px; height: 60px; background: #fff; border-radius: 12px;
		box-shadow: inset -4px -4px rgba(0,0,0,0.1), 4px 4px rgba(255,255,255,0.2);
		animation: miniTricks 4s infinite cubic-bezier(0.45, 0.05, 0.55, 0.95);
	}
	@keyframes miniTricks {
		0%, 100% { transform: translateY(0) rotate(0deg); }
		20% { transform: translateY(-40px) rotate(180deg) scaleX(0.8) scaleY(1.2); }
		40% { transform: translateY(0) rotate(360deg) scaleX(1.3) scaleY(0.7); }
		60% { transform: translateY(-20px) rotate(-10deg) scale(1.1); }
		80% { transform: translateY(0) rotate(10deg) scale(0.9); }
	}
	.performer-shadow {
		width: 40px; height: 8px; background: rgba(0,0,0,0.2); border-radius: 50%; margin-top: 10px;
		animation: shadowPulse 4s infinite;
	}
	@keyframes shadowPulse {
		0%, 100%, 40%, 80% { transform: scaleX(1); opacity: 1; }
		20%, 60% { transform: scaleX(0.5); opacity: 0.3; }
	}

	/* LAUGHING STARS */
	.credits-stars { position: absolute; inset: 0; pointer-events: none; }
	.laughing-star {
		position: absolute; bottom: -50px; left: var(--x);
		font-size: 2rem; opacity: 0.6;
		animation: starFloatUp 12s linear infinite var(--delay);
	}
	@keyframes starFloatUp {
		0% { transform: translateY(0) rotate(0deg); opacity: 0; }
		20% { opacity: 0.8; }
		100% { transform: translateY(-120vh) rotate(360deg); opacity: 0; }
	}

	.credits-close-btn {
		position: absolute; bottom: 40px; z-index: 100;
		background: #fff; border: none; border-radius: 50px;
		padding: 15px 40px; display: flex; align-items: center; gap: 15px;
		color: #2d3436; font-family: inherit; font-size: 1.5rem; font-weight: bold;
		cursor: pointer; box-shadow: 0 10px 20px rgba(0,0,0,0.3);
		transition: all 0.3s cubic-bezier(0.175, 0.885, 0.32, 1.275);
	}
	.credits-close-btn:hover { transform: scale(1.1) translateY(-5px); box-shadow: 0 15px 30px rgba(0,0,0,0.4); }
	.credits-close-btn .btn-icon { font-size: 2rem; }

	/* ============================================
	   SETTINGS ENGINE STYLES
	   ============================================ */
	.settings-overlay {
		position: absolute; inset: 0; z-index: 500;
		display: flex; align-items: center; justify-content: center;
		background: rgba(0,0,0,0.3); backdrop-filter: blur(8px);
	}
	.settings-modal {
		background: rgba(255, 255, 255, 0.9);
		width: 450px; padding: 40px; border-radius: 40px;
		border: 8px solid #74b9ff; box-shadow: 0 20px 60px rgba(0,0,0,0.4);
		position: relative; text-align: center;
	}
	.close-x {
		position: absolute; top: 15px; right: 25px;
		background: none; border: none; font-size: 2.5rem; color: #74b9ff;
		cursor: pointer; transition: transform 0.2s;
	}
	.close-x:hover { transform: scale(1.2) rotate(90deg); color: #0984e3; }

	.settings-title {
		font-size: 2rem; color: #0984e3; margin-bottom: 30px; letter-spacing: 2px;
	}
	.settings-groups { display: flex; flex-direction: column; gap: 25px; margin-bottom: 30px; }
	
	.setting-item { display: flex; flex-direction: column; align-items: center; gap: 10px; }
	.setting-item.flex-row { flex-direction: row; justify-content: space-between; }
	.setting-item label { font-weight: bold; color: #2d3436; font-size: 1.1rem; }

	/* WONDER SLIDER */
	.wonder-slider {
		-webkit-appearance: none; width: 100%; height: 12px;
		background: #dfe6e9; border-radius: 10px; outline: none;
	}
	.wonder-slider::-webkit-slider-thumb {
		-webkit-appearance: none; width: 25px; height: 25px;
		background: #74b9ff; border-radius: 50%; cursor: pointer;
		border: 4px solid #fff; box-shadow: 0 4px 10px rgba(0,0,0,0.2);
	}

	/* TOGGLE & SPEED BUTTONS */
	.toggle-btn, .speed-selector button {
		background: #dfe6e9; border: none; padding: 10px 20px;
		border-radius: 15px; font-family: inherit; font-weight: bold;
		cursor: pointer; transition: all 0.2s; color: #636e72;
	}
	.speed-selector { display: flex; gap: 10px; }
	.toggle-btn.active, .speed-selector button.active {
		background: #74b9ff; color: #fff; transform: scale(1.05);
		box-shadow: 0 5px 15px rgba(116, 185, 255, 0.4);
	}

	.apply-btn {
		width: 100%; padding: 15px; border-radius: 20px;
		background: #55efc4; border: none; color: #fff;
		font-family: inherit; font-size: 1.4rem; font-weight: bold;
		cursor: pointer; transition: all 0.3s;
		box-shadow: 0 8px 0 #00b894; margin-top: 10px;
	}
	.apply-btn:hover { transform: translateY(-3px); box-shadow: 0 11px 0 #00b894; }
	.apply-btn:active { transform: translateY(5px); box-shadow: 0 3px 0 #00b894; }

	/* PAUSE LOGIC */
	.game-paused * {
		animation-play-state: paused !important;
	}
</style>
