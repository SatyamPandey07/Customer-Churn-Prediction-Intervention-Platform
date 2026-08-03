import { NextResponse } from 'next/server';

export async function POST() {
  const response = NextResponse.json({ success: true });
  response.cookies.delete('access_token');
  response.cookies.delete('user_role');
  return response;
}
