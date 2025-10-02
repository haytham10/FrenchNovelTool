import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'Privacy Policy - French Novel Tool',
  description: 'Privacy Policy for French Novel Tool',
  robots: { index: true, follow: true },
};

export default function PrivacyPolicyPage() {
  return (
    <section style={{ maxWidth: 800, margin: '0 auto', padding: '2rem 1rem' }}>
      <h1 style={{ marginBottom: '1rem' }}>Privacy Policy</h1>
      <p><em>Last updated: {new Date().toISOString().slice(0, 10)}</em></p>

      <p>
        French Novel Tool (&quot;we&quot;, &quot;our&quot;, &quot;us&quot;) respects your privacy. This Privacy Policy explains
        what information we collect, how we use it, and your choices.
      </p>

      <h2>Information We Collect</h2>
      <ul>
        <li>
          Google account info when you sign in with Google (name, email, profile picture, and Google
          account ID).
        </li>
        <li>
          OAuth tokens only to access Google APIs you permit (e.g., Google Drive/Sheets). Tokens are
          stored securely and used solely to perform actions you request.
        </li>
        <li>
          Usage information related to processing PDFs and exporting results to Google Sheets.
        </li>
      </ul>

      <h2>How We Use Information</h2>
      <ul>
        <li>Authenticate you and maintain your session.</li>
        <li>Process your uploaded PDFs and generate sentence outputs.</li>
        <li>Create or update spreadsheets in your Google Drive when you request exports.</li>
        <li>Improve reliability, quality, and security of the service.</li>
      </ul>

      <h2>Data Sharing</h2>
      <p>
        We do not sell your personal information. We may share data with service providers strictly
        to operate the app (e.g., cloud hosting) and only as necessary. We may disclose information if
        required by law or to protect our rights.
      </p>

      <h2>Data Retention</h2>
      <p>
        We retain data only as long as needed to provide the service and comply with legal
        obligations. You can request deletion of your account data by contacting us.
      </p>

      <h2>Security</h2>
      <p>
        We implement reasonable safeguards to protect your data. However, no method of transmission
        or storage is 100% secure.
      </p>

      <h2>Your Choices</h2>
      <ul>
        <li>You may disconnect Google permissions at any time in your Google Account settings.</li>
        <li>You may contact us to request data access or deletion.</li>
      </ul>

      <h2>Contact</h2>
      <p>
        Questions about this policy? Email us at <a href="mailto:privacy@frenchnoveltool.com">privacy@frenchnoveltool.com</a>.
      </p>
    </section>
  );
}
