# Galaga Testbed - 2D Game for Reasoning Pattern Validation

## Overview

A classic Galaga-inspired 2D space shooter that serves as a testbed for temporal, spatial, and causal reasoning patterns. Gaming is a target audience for Agenkit, and Galaga provides a perfect environment with clear temporal patterns, spatial dynamics, and causal relationships.

## Why Galaga?

Galaga is ideal for testing agentic patterns because it features:

1. **Clear Temporal Patterns**: Wave timing, attack cooldowns, power-up durations
2. **Spatial Reasoning**: Ship positioning, enemy formations, bullet trajectories
3. **Causal Chains**: Actions have predictable consequences
4. **Predictive Modeling**: Enemy behavior follows patterns
5. **Real-time Decision Making**: Fast-paced gameplay tests agent responsiveness

Plus, it's a beloved classic that's fun to play and watch!

## Game Mechanics

### Core Gameplay

- **Player Ship**: Moves left/right along bottom of screen
- **Enemies**: Fly in formation patterns, dive attack periodically
- **Shooting**: Player shoots bullets upward, enemies shoot downward
- **Objective**: Destroy all enemies without getting hit
- **Lives**: 3 lives, game over when all lost
- **Waves**: Increasing difficulty with each wave

### Classic Galaga Features

#### Enemy Types
- **Boss Galaga** (Blue): Can capture player ship with tractor beam
- **Butterflies** (Red): Mid-tier enemies, worth more points
- **Bees** (Yellow): Basic enemies, form bulk of formation

#### Special Mechanics
- **Capture**: Boss can capture ship, player can rescue for dual ship power-up
- **Dive Patterns**: Enemies dive in swooping formations
- **Challenge Stages**: Bonus rounds where enemies fly patterns without shooting
- **Formation**: Enemies arrange in recognizable grid patterns

#### Scoring
- Base points per enemy type
- Combo bonuses for consecutive hits
- Perfect wave bonus
- Rescue bonus (dual ship)

## Agentic Patterns to Test

### 1. Temporal Reasoning Pattern

Understanding time, duration, and timing in the game.

```python
class GalagaTemporalAgent(Agent):
    """
    Agent that understands timing in Galaga.

    Temporal concepts:
    - Wave cycles (when next wave arrives)
    - Attack windows (safe times to shoot)
    - Enemy dive timing (predictable patterns)
    - Power-up duration
    - Cooldown periods
    """

    def __init__(self):
        self.temporal = TemporalReasoningPattern()
        self.wave_history = []
        self.timing_patterns = {}

    def predict_next_wave_timing(self, current_wave: int) -> float:
        """
        Predict when next wave will arrive.

        Learns from history:
        - Wave 1 arrives at t=0
        - Wave 2 arrives at t=30s (after wave 1 cleared)
        - Inter-wave delay: 5s

        Returns: predicted timestamp
        """
        if not self.wave_history:
            return 0.0

        avg_wave_duration = np.mean([w.duration for w in self.wave_history])
        inter_wave_delay = 5.0
        return time.time() + inter_wave_delay

    def find_attack_window(self, enemy_formation: Formation) -> Optional[TimeWindow]:
        """
        Find safe time window to attack formation.

        Considers:
        - When enemies are diving (unsafe)
        - When enemies are forming (safe)
        - When enemies are shooting (unsafe)
        - Cooldown between enemy attacks

        Returns: (start_time, end_time) or None if no safe window
        """
        current_time = time.time()
        enemy_positions = [e.position for e in enemy_formation]

        # Enemies in formation = safe
        if all(e.state == "formation" for e in enemy_formation):
            next_dive_time = self._predict_next_dive(enemy_formation)
            return (current_time, next_dive_time - 1.0)  # 1s buffer

        return None

    def predict_dive_timing(self, enemy: Enemy) -> List[float]:
        """
        Predict when enemy will dive based on historical patterns.

        Enemies dive in cycles:
        - Formation phase: 10-15s
        - Select divers: 2-3s
        - Dive attack: 3-5s
        - Return to formation: 2-3s

        Returns: list of predicted dive timestamps
        """
        if enemy.type == "boss":
            cycle_time = 20.0  # Bosses dive every 20s
        elif enemy.type == "butterfly":
            cycle_time = 15.0
        else:  # bee
            cycle_time = 12.0

        last_dive = enemy.last_dive_time
        return [last_dive + i * cycle_time for i in range(1, 6)]
```

### 2. Spatial Reasoning Pattern

Understanding position, movement, and space.

```python
class GalagaSpatialAgent(Agent):
    """
    Agent that understands spatial relationships in Galaga.

    Spatial concepts:
    - Ship position and boundaries
    - Enemy formation structure
    - Bullet trajectories
    - Collision zones
    - Safe/dangerous regions
    """

    def __init__(self):
        self.spatial = SpatialReasoningPattern()
        self.screen_bounds = (0, 0, 800, 600)  # (x, y, width, height)

    def find_safe_position(self,
                          enemies: List[Enemy],
                          enemy_bullets: List[Bullet]) -> Position:
        """
        Find safe position for ship that avoids all threats.

        Algorithm:
        1. Discretize bottom third of screen into positions
        2. For each position, calculate threat level
        3. Return position with lowest threat

        Threat factors:
        - Distance to enemy bullets (closer = higher threat)
        - Predicted bullet trajectories (on collision course = max threat)
        - Enemy positions (directly above = medium threat)
        """
        ship_y = self.screen_bounds[3] - 50  # Bottom of screen
        positions = []

        # Sample positions across bottom
        for x in range(50, self.screen_bounds[2] - 50, 10):
            threat = self._calculate_threat((x, ship_y), enemies, enemy_bullets)
            positions.append((x, ship_y, threat))

        # Return position with minimum threat
        return min(positions, key=lambda p: p[2])[:2]

    def predict_bullet_trajectory(self, bullet: Bullet, time_delta: float) -> Position:
        """
        Predict where bullet will be after time_delta seconds.

        Simple physics:
        - Constant velocity (no acceleration)
        - Straight line motion
        - position = current_position + velocity * time
        """
        return (
            bullet.x + bullet.velocity_x * time_delta,
            bullet.y + bullet.velocity_y * time_delta
        )

    def will_collide(self,
                    ship_position: Position,
                    bullet: Bullet,
                    time_horizon: float = 2.0) -> bool:
        """
        Predict if bullet will collide with ship within time_horizon.

        Algorithm:
        1. Project bullet trajectory forward in time
        2. Check if trajectory intersects ship hitbox
        3. Return True if collision predicted
        """
        ship_hitbox = self._get_hitbox(ship_position)

        # Sample trajectory at 0.1s intervals
        for t in np.arange(0, time_horizon, 0.1):
            bullet_pos = self.predict_bullet_trajectory(bullet, t)
            if self._point_in_box(bullet_pos, ship_hitbox):
                return True

        return False

    def plan_dodge_path(self,
                       current_position: Position,
                       threats: List[Bullet]) -> Path:
        """
        Plan movement path to avoid all threats.

        Uses A* pathfinding with threat-aware cost function:
        - Normal space: cost = 1
        - Near bullet trajectory: cost = 10
        - On bullet collision course: cost = inf (invalid)

        Returns: List of waypoints to follow
        """
        goal = self.find_safe_position([], threats)
        return self._astar_with_threats(current_position, goal, threats)

    def analyze_formation_structure(self, enemies: List[Enemy]) -> FormationGraph:
        """
        Understand enemy formation as spatial graph.

        Builds graph of:
        - Enemy positions (nodes)
        - Spatial relationships (edges)
          - adjacent (side-by-side)
          - above/below (vertical neighbors)
          - formation_leader (boss at front)

        Useful for:
        - Identifying high-value targets (center of formation)
        - Finding weak points (gaps in formation)
        - Predicting dive order (edge enemies dive first)
        """
        graph = {}
        for enemy in enemies:
            neighbors = self._find_spatial_neighbors(enemy, enemies)
            graph[enemy.id] = {
                "position": enemy.position,
                "neighbors": neighbors,
                "role": self._classify_formation_role(enemy, enemies)
            }
        return graph
```

### 3. Causal Reasoning Pattern

Understanding cause and effect.

```python
class GalagaCausalAgent(Agent):
    """
    Agent that understands cause and effect in Galaga.

    Causal concepts:
    - Actions cause state changes
    - Events have consequences
    - Causal chains (A causes B causes C)
    - Counterfactual reasoning ("what if?")
    """

    def __init__(self):
        self.causal = CausalReasoningPattern()
        self.action_history = []

    def predict_action_outcome(self,
                              action: Action,
                              state: GameState) -> GameState:
        """
        Predict game state after taking action.

        Causal model:
        - shoot() -> bullet spawned -> (if hit) enemy destroyed -> score increased
        - move_left() -> ship.x -= speed -> (if collision) life lost
        - wait() -> state mostly unchanged (but time passes, enemies move)

        Returns: predicted next state
        """
        next_state = state.copy()

        if action.type == "shoot":
            # Spawn bullet
            bullet = Bullet(position=state.ship.position, velocity=(0, -5))
            next_state.player_bullets.append(bullet)

            # Check if bullet will hit enemy
            for enemy in state.enemies:
                if self._will_hit(bullet, enemy):
                    next_state.enemies.remove(enemy)
                    next_state.score += enemy.points
                    break

        elif action.type == "move":
            # Update ship position
            next_state.ship.position = (
                state.ship.position[0] + action.direction * state.ship.speed,
                state.ship.position[1]
            )

            # Check for collisions
            for bullet in state.enemy_bullets:
                if self._check_collision(next_state.ship, bullet):
                    next_state.lives -= 1

        return next_state

    def explain_death(self, death_state: GameState) -> CausalChain:
        """
        Explain causal chain that led to death.

        Example chain:
        1. Enemy dove from formation
        2. Enemy fired bullet
        3. Ship was positioned below enemy
        4. Ship did not dodge
        5. Bullet hit ship
        6. Life lost

        Identifies:
        - Root cause (why did this happen?)
        - Preventable actions (what could have been done?)
        - Lesson learned (how to avoid in future?)
        """
        chain = []

        # Find collision event
        collision_event = self._find_collision_event(death_state)
        chain.append({
            "event": "collision",
            "cause": "ship_position = bullet_position",
            "time": collision_event.time
        })

        # Trace back: why was bullet there?
        bullet = collision_event.bullet
        chain.append({
            "event": "bullet_fired",
            "cause": f"enemy {bullet.source_id} fired bullet",
            "time": bullet.spawn_time
        })

        # Why did enemy fire?
        enemy = self._find_enemy(bullet.source_id, death_state)
        chain.append({
            "event": "enemy_dive",
            "cause": f"enemy {enemy.id} dove from formation",
            "time": enemy.dive_start_time
        })

        # What could have been done?
        prevention = self._analyze_prevention(chain, death_state)

        return CausalChain(
            events=reversed(chain),  # Chronological order
            root_cause=chain[-1],
            prevention_opportunities=prevention,
            lesson="Dodge when enemy dives directly overhead"
        )

    def plan_high_score_strategy(self, state: GameState) -> Strategy:
        """
        Plan actions to maximize score using causal understanding.

        Causal strategies:
        - Combo kills: Rapid kills -> multiplier -> bonus points
        - Perfect wave: No misses -> perfect bonus
        - Boss kill: Kill boss when captured ship -> dual ship -> 2x firepower
        - Challenge stage: Hit all enemies -> huge bonus

        Returns: Ordered list of high-value actions
        """
        strategies = []

        # Combo strategy
        if state.combo_count > 0:
            strategies.append({
                "name": "maintain_combo",
                "reason": "Combo multiplier active, keep killing quickly",
                "actions": [self._target_weakest_enemy(state)],
                "expected_bonus": state.combo_count * 100
            })

        # Boss capture strategy
        if state.ship_captured and self._boss_exists(state):
            strategies.append({
                "name": "rescue_ship",
                "reason": "Kill boss to gain dual ship power-up",
                "actions": [self._target_boss(state)],
                "expected_bonus": 1000 + "dual_firepower"
            })

        # Perfect wave strategy
        if state.shots_fired < state.enemies_remaining:
            strategies.append({
                "name": "perfect_wave",
                "reason": "Can still achieve perfect wave",
                "actions": [self._aim_carefully(state)],
                "expected_bonus": 5000
            })

        # Choose highest value strategy
        return max(strategies, key=lambda s: s["expected_bonus"])
```

### 4. World Model Integration

Combining all patterns into complete understanding.

```python
class GalagaWorldModel(Agent):
    """
    Complete world understanding for Galaga.

    Integrates:
    - Temporal reasoning (timing patterns)
    - Spatial reasoning (positions, trajectories)
    - Causal reasoning (action outcomes)

    Provides:
    - Predictive game state modeling
    - Strategic planning
    - Autonomous play
    """

    def __init__(self):
        self.temporal = GalagaTemporalAgent()
        self.spatial = GalagaSpatialAgent()
        self.causal = GalagaCausalAgent()

        self.state_history = []
        self.performance_metrics = {}

    async def process(self, message: Message) -> Message:
        """Main agent loop."""
        game_state = self._parse_game_state(message.content)

        # Update understanding
        self._update_world_model(game_state)

        # Decide action
        action = self.decide_action(game_state)

        return Message(
            role="agent",
            content=json.dumps({"action": action.to_dict()})
        )

    def decide_action(self, state: GameState) -> Action:
        """
        Decide best action using complete world understanding.

        Decision process:
        1. Spatial: Am I in danger? (immediate threat detection)
        2. Temporal: Is it a good time to attack? (timing analysis)
        3. Causal: What will happen if I act? (outcome prediction)
        4. Strategic: Which action maximizes long-term reward?

        Returns: Best action to take
        """
        # IMMEDIATE THREATS (spatial)
        immediate_threats = self._detect_threats(state)
        if immediate_threats:
            # Dodge is priority
            safe_position = self.spatial.find_safe_position(
                state.enemies,
                state.enemy_bullets
            )
            return MoveAction(target=safe_position)

        # ATTACK OPPORTUNITIES (temporal + spatial)
        attack_window = self.temporal.find_attack_window(state.enemies)
        if attack_window and self._has_clear_shot(state):
            target = self._select_target(state)
            return ShootAction(target=target)

        # STRATEGIC POSITIONING (causal + spatial)
        # No immediate threats, position for next wave
        optimal_position = self._calculate_optimal_position(state)
        return MoveAction(target=optimal_position)

    def predict_future_state(self,
                            current: GameState,
                            actions: List[Action],
                            time_horizon: float = 5.0) -> List[GameState]:
        """
        Predict future game states from action sequence.

        Simulates game forward:
        1. Apply actions to state (causal)
        2. Predict enemy movements (temporal + spatial)
        3. Check for collisions (spatial)
        4. Update scores and status (causal)

        Returns: Predicted state trajectory
        """
        states = [current]
        dt = 0.1  # 100ms time steps

        for t in np.arange(0, time_horizon, dt):
            prev_state = states[-1]

            # Get action for this timestep
            action_idx = int(t // (time_horizon / len(actions)))
            action = actions[min(action_idx, len(actions) - 1)]

            # Predict next state
            next_state = self.causal.predict_action_outcome(action, prev_state)

            # Predict enemy movements
            next_state = self._predict_enemy_movements(next_state, dt)

            # Predict bullet movements
            next_state = self._predict_bullet_movements(next_state, dt)

            states.append(next_state)

        return states

    def plan_wave_strategy(self, wave: Wave) -> Strategy:
        """
        Plan complete strategy for wave.

        Combines all reasoning:
        - Temporal: When to attack each phase
        - Spatial: Where to position for each phase
        - Causal: How actions lead to victory

        Returns: Multi-phase strategy
        """
        strategy = Strategy(wave_number=wave.number)

        # Phase 1: Formation phase (enemies forming up)
        strategy.add_phase({
            "name": "formation_phase",
            "duration": self.temporal.predict_formation_time(wave),
            "goal": "Survive, pick off weak enemies",
            "position": "center_bottom",
            "tactics": ["defensive_shooting", "avoid_dives"]
        })

        # Phase 2: Attack phase (enemies formed, attacking)
        strategy.add_phase({
            "name": "attack_phase",
            "duration": 20.0,  # Variable
            "goal": "Destroy formation systematically",
            "position": "mobile_defensive",
            "tactics": ["target_edges_first", "maintain_combo", "dodge_bullets"]
        })

        # Phase 3: Cleanup phase (few enemies remain)
        strategy.add_phase({
            "name": "cleanup_phase",
            "duration": 10.0,
            "goal": "Perfect wave, maximum score",
            "position": "aggressive",
            "tactics": ["hunt_remaining", "avoid_risks", "perfect_accuracy"]
        })

        return strategy
```

## Implementation Plan

### Phase 1: Game Engine (2 weeks)

**Goal**: Playable Galaga game (human player)

**Tasks**:
- [ ] Pygame setup and game loop
- [ ] Ship rendering and controls
- [ ] Enemy rendering and formations
- [ ] Shooting mechanics (player and enemy)
- [ ] Collision detection
- [ ] Scoring system
- [ ] Wave progression
- [ ] Lives and game over

**Deliverable**: `python play.py` starts playable game

### Phase 2: Temporal Pattern (1 week)

**Goal**: Agent understands timing

**Tasks**:
- [ ] Wave timing prediction
- [ ] Attack window detection
- [ ] Dive pattern recognition
- [ ] Cooldown tracking
- [ ] Temporal pattern extraction

**Deliverable**: Agent that times attacks optimally

### Phase 3: Spatial Pattern (1 week)

**Goal**: Agent understands space

**Tasks**:
- [ ] Safe position finding
- [ ] Trajectory prediction
- [ ] Collision avoidance
- [ ] Formation analysis
- [ ] Path planning

**Deliverable**: Agent that dodges effectively

### Phase 4: Causal Pattern (1 week)

**Goal**: Agent understands cause-effect

**Tasks**:
- [ ] Action outcome prediction
- [ ] Death cause analysis
- [ ] Strategy planning
- [ ] High-score optimization
- [ ] Causal chain tracking

**Deliverable**: Agent that makes strategic decisions

### Phase 5: World Model (2 weeks)

**Goal**: Autonomous agent plays Galaga

**Tasks**:
- [ ] Integrate all patterns
- [ ] State prediction
- [ ] Complete strategy planning
- [ ] Performance optimization
- [ ] Autonomous play mode

**Deliverable**: Agent that completes wave 5+

### Phase 6: Pattern Extraction (1 week)

**Goal**: Reusable patterns for other games

**Tasks**:
- [ ] Extract game-agnostic patterns
- [ ] Document pattern APIs
- [ ] Create pattern library
- [ ] Apply to second game (validation)

**Deliverable**: `agenkit.patterns.gaming` module

## Technical Stack

### Core Dependencies
```
pygame>=2.5.0           # Game rendering
numpy>=1.24.0           # Fast array operations
opencv-python>=4.8.0    # Visual debugging (optional)
```

### Agenkit Integration
```
agenkit>=0.29.0         # Agent framework
```

### Development
```
pytest>=7.4.0           # Testing
black>=23.0.0           # Code formatting
mypy>=1.5.0             # Type checking
```

## File Structure

```
agenkit/examples/galaga/
├── README.md                    # Quick start guide
├── requirements.txt             # Dependencies
├── game/
│   ├── __init__.py
│   ├── engine.py               # Core game loop
│   ├── entities.py             # Ship, Enemy, Bullet classes
│   ├── physics.py              # Movement, collision
│   ├── rendering.py            # Pygame drawing
│   └── constants.py            # Game constants
├── agents/
│   ├── __init__.py
│   ├── temporal_agent.py       # Temporal reasoning
│   ├── spatial_agent.py        # Spatial reasoning
│   ├── causal_agent.py         # Causal reasoning
│   └── world_model_agent.py    # Complete agent
├── patterns/
│   ├── __init__.py
│   ├── temporal.py             # Temporal pattern
│   ├── spatial.py              # Spatial pattern
│   └── causal.py               # Causal pattern
├── tests/
│   ├── test_game.py
│   ├── test_temporal.py
│   ├── test_spatial.py
│   └── test_causal.py
├── assets/
│   ├── sprites/
│   │   ├── ship.png
│   │   ├── boss.png
│   │   ├── butterfly.png
│   │   └── bee.png
│   └── sounds/
│       ├── shoot.wav
│       ├── explosion.wav
│       └── game_over.wav
├── play.py                     # Human playable
├── train.py                    # Train agent (optional RL)
├── demo.py                     # Watch agent play
└── analyze.py                  # Analyze agent performance
```

## Success Metrics

### Pattern Validation
- ✅ Temporal reasoning: 85%+ accuracy predicting enemy timing
- ✅ Spatial reasoning: 90%+ successful collision avoidance
- ✅ Causal reasoning: 80%+ correct outcome predictions

### Agent Performance
- ✅ Complete wave 1: 90%+ success rate
- ✅ Complete wave 3: 75%+ success rate
- ✅ Complete wave 5: 50%+ success rate
- 🎯 High score: Top 10% of human players (stretch goal)

### Pattern Reusability
- ✅ Extract 3+ reusable patterns
- ✅ Apply patterns to second game (Space Invaders)
- ✅ Demonstrate 80%+ code reuse between games

## Future Extensions

### More 2D Games
- **Space Invaders**: Similar mechanics, validate pattern transfer
- **Asteroids**: Continuous movement, 360° rotation, different spatial reasoning
- **Pac-Man**: Navigation, path planning, adversarial reasoning

### 3D Extension
Once 2D patterns are solid, extend to 3D space shooters

### Multi-Agent
- Cooperative: Multiple ships, shared score
- Competitive: 2 players, competition for kills
- Swarm: Multiple agents with emergent behavior

### Learning
- Reinforcement learning for strategy optimization
- Imitation learning from human players
- Self-play for pattern discovery

## Related Research

- DeepMind's Atari agents (DQN, Rainbow)
- OpenAI Five (predictive world models)
- Game-playing agents as testbeds for AI research

## Community Building

This example supports the gaming community by:
1. **Working Example**: Complete, playable agent
2. **Educational**: Learn patterns through games
3. **Extensible**: Easy to modify and experiment
4. **Fun**: Nostalgic game, satisfying to watch agent master
5. **Research Platform**: Test new patterns in game environment

## Related Issues

- Agenkit: Core temporal/spatial/causal patterns
- Endless #14-18: World models and reasoning patterns
- Gaming community: Target audience engagement
