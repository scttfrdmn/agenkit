/*
Fallback Composition Example

WHY USE FALLBACK COMPOSITION?
-----------------------------
1. Reliability: Handle service outages gracefully
2. Cost Optimization: Try cheap options before expensive ones
3. Graceful Degradation: Maintain functionality when primary fails
4. Quality Tiers: Premium → Standard → Basic fallback chain
5. Geographic Failover: Primary region → Secondary region

WHEN TO USE:
- High-availability requirements (99.9%+ uptime)
- Multi-tier service offerings (premium/standard/free)
- Cost-sensitive applications (try free options first)
- Services with rate limits
- Multi-region deployments
- External API dependencies

WHEN NOT TO USE:
- All options must succeed (use SequentialAgent with validation)
- Need results from all options (use ParallelAgent)
- Fallback masks underlying issues (fix root cause instead)
- Performance requirements don't allow retry latency

TRADE-OFFS:
- Reliability: Much higher availability vs complexity
- Cost: Try cheaper options first vs potential quality reduction
- Latency: Additional retries add delay vs maintained functionality

Run with: go run agenkit-go/examples/composition/fallback_example.go
*/

package main

import (
	"context"
	"fmt"
	"math/rand"
	"strings"
	"time"

	"github.com/agenkit/agenkit-go/agenkit"
	"github.com/agenkit/agenkit-go/composition"
)

// PremiumLLM is expensive, high quality, rate limited
type PremiumLLM struct {
	requests int
	quota    int
}

func NewPremiumLLM(quota int) *PremiumLLM {
	return &PremiumLLM{quota: quota}
}

func (a *PremiumLLM) Name() string { return "gpt-4" }
func (a *PremiumLLM) Capabilities() []string { return []string{"text_generation", "premium"} }

func (a *PremiumLLM) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	a.requests++

	// Simulate rate limiting
	if a.requests > a.quota {
		return nil, fmt.Errorf("rate limit exceeded: GPT-4 quota exhausted")
	}

	time.Sleep(300 * time.Millisecond)

	return agenkit.NewMessage("agent", "Premium response: High-quality analysis with detailed reasoning.").
		WithMetadata("model", "gpt-4").
		WithMetadata("cost", 0.03).
		WithMetadata("quality", 0.95), nil
}

// StandardLLM is moderate cost and quality
type StandardLLM struct {
	failureRate float64
}

func NewStandardLLM(failureRate float64) *StandardLLM {
	return &StandardLLM{failureRate: failureRate}
}

func (a *StandardLLM) Name() string { return "gpt-3.5-turbo" }
func (a *StandardLLM) Capabilities() []string { return []string{"text_generation", "standard"} }

func (a *StandardLLM) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Simulate occasional failures
	if rand.Float64() < a.failureRate {
		return nil, fmt.Errorf("service temporarily unavailable: 503")
	}

	time.Sleep(150 * time.Millisecond)

	return agenkit.NewMessage("agent", "Standard response: Good quality answer.").
		WithMetadata("model", "gpt-3.5-turbo").
		WithMetadata("cost", 0.002).
		WithMetadata("quality", 0.80), nil
}

// BasicLLM is cheap, always available, lower quality
type BasicLLM struct{}

func (a *BasicLLM) Name() string { return "llama-3-8b" }
func (a *BasicLLM) Capabilities() []string { return []string{"text_generation", "basic"} }

func (a *BasicLLM) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Always succeeds (local model)
	time.Sleep(50 * time.Millisecond)

	return agenkit.NewMessage("agent", "Basic response: Simple answer.").
		WithMetadata("model", "llama-3-8b").
		WithMetadata("cost", 0.0).
		WithMetadata("quality", 0.65), nil
}

// Example 1: Cost optimization fallback chain
func example1CostOptimization() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("EXAMPLE 1: Cost Optimization")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nUse case: Try cheap options before expensive ones")

	// Create fallback chain: Premium → Standard → Basic
	costOptimizer, _ := composition.NewFallbackAgent("cost-optimized-llm",
		NewPremiumLLM(5), // Limited quota
		NewStandardLLM(0.2), // 20% failure rate
		&BasicLLM{},
	)

	fmt.Println("\nProcessing 10 requests with cost optimization...")
	fmt.Println("Strategy: Try GPT-4 → GPT-3.5 → Llama-3")

	ctx := context.Background()
	var totalCost float64
	modelUsage := make(map[string]int)

	for i := 0; i < 10; i++ {
		result, err := costOptimizer.Process(ctx, agenkit.NewMessage("user", fmt.Sprintf("Request %d: Analyze this", i+1)))
		if err != nil {
			fmt.Printf("Request %d: All fallbacks failed: %v\n", i+1, err)
			continue
		}

		model := result.Metadata["model"].(string)
		cost := result.Metadata["cost"].(float64)
		quality := result.Metadata["quality"].(float64)

		totalCost += cost
		modelUsage[model]++

		fmt.Printf("Request %d: %s (cost: $%.4f, quality: %.2f)\n", i+1, model, cost, quality)
	}

	// Analysis
	fmt.Println("\nCost Analysis:")
	fmt.Printf("  Total Cost: $%.4f\n", totalCost)
	fmt.Printf("  Average Cost per Request: $%.4f\n", totalCost/10)

	fmt.Println("\n  Model Distribution:")
	for model, count := range modelUsage {
		fmt.Printf("    %s: %d/10 requests\n", model, count)
	}

	fmt.Println("\nCOST OPTIMIZATION STRATEGY:")
	fmt.Println("  - First 5 requests: Use GPT-4 (within quota)")
	fmt.Println("  - After quota: Fallback to GPT-3.5 (15× cheaper)")
	fmt.Println("  - If GPT-3.5 fails: Fallback to local Llama (free)")
	fmt.Println("  - Result: Maintain service with 50-90% cost savings")
}

// RegionalService simulates a service in a specific region
type RegionalService struct {
	region      string
	failureRate float64
}

func NewRegionalService(region string, failureRate float64) *RegionalService {
	return &RegionalService{region: region, failureRate: failureRate}
}

func (a *RegionalService) Name() string { return fmt.Sprintf("service-%s", a.region) }
func (a *RegionalService) Capabilities() []string { return []string{"processing"} }

func (a *RegionalService) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Simulate regional outage
	if rand.Float64() < a.failureRate {
		return nil, fmt.Errorf("region %s unavailable: network timeout", a.region)
	}

	time.Sleep(100 * time.Millisecond)

	return agenkit.NewMessage("agent", fmt.Sprintf("Processed in %s", a.region)).
		WithMetadata("region", a.region), nil
}

// Example 2: Geographic failover
func example2GeographicFailover() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("EXAMPLE 2: Geographic Failover")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nUse case: Multi-region deployment for reliability")

	// Create geographic fallback: Primary → Secondary → Tertiary
	haService, _ := composition.NewFallbackAgent("ha-service",
		NewRegionalService("us-east-1", 0.3),
		NewRegionalService("us-west-2", 0.3),
		NewRegionalService("eu-west-1", 0.3),
	)

	fmt.Println("\nSimulating 20 requests with 30% regional failure rate...")
	fmt.Println("Regions: us-east-1 → us-west-2 → eu-west-1")

	ctx := context.Background()
	regionUsage := make(map[string]int)
	successes := 0

	for i := 0; i < 20; i++ {
		result, err := haService.Process(ctx, agenkit.NewMessage("user", fmt.Sprintf("Request %d", i+1)))
		if err != nil {
			fmt.Printf("Request %d: All regions failed\n", i+1)
			continue
		}

		region := result.Metadata["region"].(string)
		regionUsage[region]++
		successes++
	}

	fmt.Println("\nAvailability Analysis:")
	fmt.Printf("  Successful Requests: %d/20 (%.0f%%)\n", successes, float64(successes)/20*100)

	fmt.Println("\n  Region Distribution:")
	for region, count := range regionUsage {
		fmt.Printf("    %s: %d requests\n", region, count)
	}

	// Calculate theoretical availability
	singleRegion := 0.7 // 1 - 0.3 failure rate
	multiRegion := 1 - (0.3 * 0.3 * 0.3) // Probability at least one works

	fmt.Println("\nHIGH AVAILABILITY BENEFITS:")
	fmt.Printf("  Single Region: ~%.0f%% availability\n", singleRegion*100)
	fmt.Printf("  3 Regions:     ~%.1f%% availability\n", multiRegion*100)
	fmt.Println("  Improvement:   27% → 99.9% uptime SLA achievable")
}

// QualityTier agents for graceful degradation
type HighQualityAgent struct{}

func (a *HighQualityAgent) Name() string { return "high-quality" }
func (a *HighQualityAgent) Capabilities() []string { return []string{"analysis"} }

func (a *HighQualityAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Fail if system is under load
	if rand.Float64() < 0.4 { // 40% failure under load
		return nil, fmt.Errorf("system overloaded: high quality service unavailable")
	}

	time.Sleep(500 * time.Millisecond)

	return agenkit.NewMessage("agent", "Detailed analysis with citations, reasoning, and examples.").
		WithMetadata("quality", "high").
		WithMetadata("detail_level", 5), nil
}

type MediumQualityAgent struct{}

func (a *MediumQualityAgent) Name() string { return "medium-quality" }
func (a *MediumQualityAgent) Capabilities() []string { return []string{"analysis"} }

func (a *MediumQualityAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// More reliable
	if rand.Float64() < 0.2 {
		return nil, fmt.Errorf("service degraded")
	}

	time.Sleep(200 * time.Millisecond)

	return agenkit.NewMessage("agent", "Good analysis with key points.").
		WithMetadata("quality", "medium").
		WithMetadata("detail_level", 3), nil
}

type LowQualityAgent struct{}

func (a *LowQualityAgent) Name() string { return "low-quality" }
func (a *LowQualityAgent) Capabilities() []string { return []string{"analysis"} }

func (a *LowQualityAgent) Process(ctx context.Context, message *agenkit.Message) (*agenkit.Message, error) {
	// Always succeeds
	time.Sleep(50 * time.Millisecond)

	return agenkit.NewMessage("agent", "Basic summary.").
		WithMetadata("quality", "low").
		WithMetadata("detail_level", 1), nil
}

// Example 3: Graceful degradation
func example3GracefulDegradation() {
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("EXAMPLE 3: Graceful Degradation")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nUse case: Maintain service quality during high load")

	qualityFallback, _ := composition.NewFallbackAgent("adaptive-quality",
		&HighQualityAgent{},
		&MediumQualityAgent{},
		&LowQualityAgent{},
	)

	fmt.Println("\nProcessing 15 requests under variable load...")
	fmt.Println("Quality tiers: High → Medium → Low")

	ctx := context.Background()
	qualityCounts := map[string]int{"high": 0, "medium": 0, "low": 0}

	for i := 0; i < 15; i++ {
		result, _ := qualityFallback.Process(ctx, agenkit.NewMessage("user", fmt.Sprintf("Request %d", i+1)))

		quality := result.Metadata["quality"].(string)
		detail := result.Metadata["detail_level"].(int)
		qualityCounts[quality]++

		fmt.Printf("Request %d: %s quality (detail level: %d)\n", i+1, quality, detail)
	}

	fmt.Println("\nQuality Distribution:")
	fmt.Printf("  High:   %d/15 (%.0f%%)\n", qualityCounts["high"], float64(qualityCounts["high"])/15*100)
	fmt.Printf("  Medium: %d/15 (%.0f%%)\n", qualityCounts["medium"], float64(qualityCounts["medium"])/15*100)
	fmt.Printf("  Low:    %d/15 (%.0f%%)\n", qualityCounts["low"], float64(qualityCounts["low"])/15*100)

	fmt.Println("\nGRACEFUL DEGRADATION:")
	fmt.Println("  - System overload → Reduce quality, not availability")
	fmt.Println("  - Users get *some* response (better than error)")
	fmt.Println("  - Can show quality indicator to user")
	fmt.Println("  - Automatically recovers when load decreases")
}

func main() {
	// Seed random for demonstration
	rand.Seed(time.Now().UnixNano())

	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("FALLBACK COMPOSITION EXAMPLES FOR AGENKIT-GO")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println("\nFallback composition builds reliable systems through redundancy.")
	fmt.Println("Try agents in order until one succeeds.")

	// Run examples
	example1CostOptimization()
	example2GeographicFailover()
	example3GracefulDegradation()

	// Summary
	fmt.Println("\n" + strings.Repeat("=", 80))
	fmt.Println("KEY TAKEAWAYS")
	fmt.Println(strings.Repeat("=", 80))
	fmt.Println(`
1. Use fallback composition when:
   - High availability is critical (99.9%+ uptime)
   - Have multiple tiers of service quality
   - Cost optimization through cheaper alternatives
   - External dependencies may fail
   - Geographic redundancy needed

2. Fallback ordering strategies:
   - Cost: Cheap → Expensive (optimize cost)
   - Quality: High → Low (graceful degradation)
   - Reliability: Primary → Secondary → Tertiary (HA)
   - Speed: Fast → Slow (optimize latency first)

3. Reliability math:
   - Single service: 90% → 90% availability
   - 2-tier fallback: 90% + 10% × 90% = 99% availability
   - 3-tier fallback: 99% + 1% × 90% = 99.9% availability
   - Each tier adds "nines" to your SLA

4. When NOT to use:
   - Fallback masks root cause issues
   - All options must execute (use ParallelAgent)
   - Latency from retries unacceptable
   - No meaningful alternatives available

REAL-WORLD PATTERNS:
✓ Multi-region: us-east → us-west → eu-west
✓ Cost tiers: GPT-4 → GPT-3.5 → local model
✓ Quality: Premium → standard → basic
✓ Auth: Authenticated → public service
✓ Circuit breaker: Primary → backup

TRADE-OFF SUMMARY:
✓ Pros: High availability, cost optimization, graceful degradation
✗ Cons: Latency from retries, masks underlying issues
→ Choose when: Reliability requirements > latency sensitivity

Next steps:
- See sequential_example.go for pipeline patterns
- See parallel_example.go for concurrent execution
- See conditional_example.go for routing patterns
	`)
}
