import Link from 'next/link';

export default function LandingPage() {
  return (
    <div className="min-h-screen">
      {/* Hero Section */}
      <div className="relative overflow-hidden bg-gradient-to-b from-primary/10 to-background">
        <div className="container mx-auto px-4 py-20">
          <div className="text-center max-w-4xl mx-auto">
            <h1 className="text-5xl lg:text-7xl font-bold mb-6 bg-gradient-to-r from-primary to-secondary bg-clip-text text-transparent">
              Smart Grant Finder
            </h1>
            <p className="text-xl lg:text-2xl text-muted-foreground mb-8">
              AI-powered grant discovery and application assistance.
              <br />
              Find funding opportunities in seconds, not hours.
            </p>
            <div className="flex gap-4 justify-center">
              <Link
                href="/auth/signup"
                className="px-8 py-3 bg-primary text-primary-foreground rounded-lg font-semibold hover:bg-primary/90 transition"
              >
                Get Started
              </Link>
              <Link
                href="/auth/signin"
                className="px-8 py-3 border-2 border-primary text-primary rounded-lg font-semibold hover:bg-primary/10 transition"
              >
                Sign In
              </Link>
            </div>
          </div>
        </div>
      </div>

      {/* Features */}
      <div className="container mx-auto px-4 py-20">
        <div className="grid md:grid-cols-3 gap-8">
          <div className="p-6 border rounded-lg">
            <div className="text-4xl mb-4">🤖</div>
            <h3 className="text-xl font-bold mb-2">AI-Powered Search</h3>
            <p className="text-muted-foreground">
              DeepSeek AI analyzes thousands of grants to find perfect matches for your needs.
            </p>
          </div>

          <div className="p-6 border rounded-lg">
            <div className="text-4xl mb-4">💬</div>
            <h3 className="text-xl font-bold mb-2">Chat Interface</h3>
            <p className="text-muted-foreground">
              Natural conversation to discover grants. Just ask what you need.
            </p>
          </div>

          <div className="p-6 border rounded-lg">
            <div className="text-4xl mb-4">⚡</div>
            <h3 className="text-xl font-bold mb-2">Automated Searches</h3>
            <p className="text-muted-foreground">
              Set up automated daily searches. Never miss a deadline.
            </p>
          </div>

          <div className="p-6 border rounded-lg">
            <div className="text-4xl mb-4">📝</div>
            <h3 className="text-xl font-bold mb-2">Application Help</h3>
            <p className="text-muted-foreground">
              AI assists with grant applications using your uploaded documents.
            </p>
          </div>

          <div className="p-6 border rounded-lg">
            <div className="text-4xl mb-4">💰</div>
            <h3 className="text-xl font-bold mb-2">Transparent Pricing</h3>
            <p className="text-muted-foreground">
              Pay as you go. $10 for 10 credits, $20 for 22 credits (11% bonus).
            </p>
          </div>

          <div className="p-6 border rounded-lg">
            <div className="text-4xl mb-4">🎯</div>
            <h3 className="text-xl font-bold mb-2">Smart Matching</h3>
            <p className="text-muted-foreground">
              Relevance scoring ensures you see the best opportunities first.
            </p>
          </div>
        </div>
      </div>

      {/* Pricing */}
      <div className="bg-muted py-20">
        <div className="container mx-auto px-4">
          <h2 className="text-4xl font-bold text-center mb-12">Simple Pricing</h2>
          <div className="grid md:grid-cols-2 gap-8 max-w-4xl mx-auto">
            <div className="bg-background p-8 rounded-lg border">
              <h3 className="text-2xl font-bold mb-2">Tier 1</h3>
              <div className="text-4xl font-bold mb-4">$10</div>
              <p className="text-muted-foreground mb-6">10 credits • $1 per credit</p>
              <ul className="space-y-2 mb-6">
                <li>✓ AI-powered search</li>
                <li>✓ Chat interface</li>
                <li>✓ Document storage</li>
                <li>✓ Email notifications</li>
              </ul>
              <Link
                href="/auth/signup"
                className="block text-center px-6 py-3 bg-primary text-primary-foreground rounded-lg hover:bg-primary/90"
              >
                Get Started
              </Link>
            </div>

            <div className="bg-primary text-primary-foreground p-8 rounded-lg border-2 border-primary relative">
              <div className="absolute -top-4 left-1/2 -translate-x-1/2 bg-secondary text-secondary-foreground px-4 py-1 rounded-full text-sm font-semibold">
                BEST VALUE
              </div>
              <h3 className="text-2xl font-bold mb-2">Tier 2</h3>
              <div className="text-4xl font-bold mb-4">$20</div>
              <p className="opacity-90 mb-6">22 credits • 11% bonus!</p>
              <ul className="space-y-2 mb-6 opacity-90">
                <li>✓ Everything in Tier 1</li>
                <li>✓ 2 extra credits FREE</li>
                <li>✓ Better value per search</li>
                <li>✓ Priority support</li>
              </ul>
              <Link
                href="/auth/signup"
                className="block text-center px-6 py-3 bg-background text-foreground rounded-lg hover:bg-background/90"
              >
                Get Started
              </Link>
            </div>
          </div>
          <p className="text-center text-muted-foreground mt-8">
            Top-ups available at $5 minimum • No monthly fees
          </p>
        </div>
      </div>

      {/* Footer */}
      <div className="border-t py-8">
        <div className="container mx-auto px-4 text-center text-muted-foreground">
          <p>© 2025 Smart Grant Finder. Powered by DeepSeek AI.</p>
        </div>
      </div>
    </div>
  );
}
