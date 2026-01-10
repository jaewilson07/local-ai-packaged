'use client'

import { signIn } from 'next-auth/react'
import { Button } from '@/components/ui/button'

export default function SignInPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center p-24">
      <div className="z-10 max-w-md w-full space-y-4">
        <h1 className="text-4xl font-bold text-center">Sign In</h1>
        <p className="text-center text-muted-foreground">
          Sign in with Discord to access Immich Social
        </p>
        <Button
          onClick={() => signIn('discord', { callbackUrl: '/feed' })}
          className="w-full"
        >
          Sign in with Discord
        </Button>
      </div>
    </div>
  )
}
