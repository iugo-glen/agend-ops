import NextAuth from 'next-auth';
import Google from 'next-auth/providers/google';

const ALLOWED_EMAIL = 'glen@iugo.com.au';

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    Google({
      clientId: process.env.GOOGLE_CLIENT_ID!,
      clientSecret: process.env.GOOGLE_CLIENT_SECRET!,
    }),
  ],
  callbacks: {
    signIn({ profile }) {
      return profile?.email === ALLOWED_EMAIL;
    },
  },
  pages: {
    signIn: '/login',
  },
});
