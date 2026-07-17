import { NextResponse } from 'next/server';

export async function POST(request: Request) {
  const { agent, message } = await request.json();
  // TODO: Replace with actual agent service integration
  const reply = `Echo from ${agent} agent: ${message}`;
  return NextResponse.json({ reply });
}