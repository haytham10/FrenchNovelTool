import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Terms of Service - French Novel Tool',
  description: 'Terms of Service for French Novel Tool',
  robots: { index: true, follow: true },
};

export default function TermsPage() {
  return (
    <section style={{ maxWidth: 800, margin: '0 auto', padding: '2rem 1rem' }}>
      <h1 style={{ marginBottom: '1rem' }}>Terms of Service</h1>
      <p><em>Last updated: {new Date().toISOString().slice(0, 10)}</em></p>

      <p>
        By accessing or using French Novel Tool (the &quot;Service&quot;), you agree to these Terms of
        Service (&quot;Terms&quot;). If you do not agree, do not use the Service.
      </p>

      <h2>Use of Service</h2>
      <ul>
        <li>You must comply with applicable laws and these Terms.</li>
        <li>You agree not to misuse the Service or attempt to disrupt it.</li>
      </ul>

      <h2>Accounts &amp; Authentication</h2>
      <p>
        You may sign in with Google to use certain features. You are responsible for activities
        under your account and for maintaining the security of your credentials.
      </p>

      <h2>User Content</h2>
      <p>
        You retain ownership of content you upload (e.g., PDFs). You grant us a limited license to
        process such content to provide the Service.
      </p>

      <h2>Third-Party Services</h2>
      <p>
        The Service integrates with Google APIs (e.g., Drive/Sheets). Your use of those services is
        subject to Google&apos;s terms and privacy policies.
      </p>

      <h2>Disclaimer</h2>
      <p>The Service is provided &quot;as is&quot; without warranties of any kind.</p>

      <h2>Limitation of Liability</h2>
      <p>
        To the maximum extent permitted by law, we are not liable for any indirect or consequential
        damages arising from your use of the Service.
      </p>

      <h2>Changes</h2>
      <p>
        We may update these Terms from time to time. Continued use of the Service constitutes
        acceptance of the updated Terms.
      </p>

      <h2>Contact</h2>
      <p>
        Questions about these Terms? Email us at <a href="mailto:legal@frenchnoveltool.com">legal@frenchnoveltool.com</a>.
      </p>
    </section>
  );
}
