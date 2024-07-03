using System.Diagnostics;
using System.Net.Sockets;
using Discord;
using Discord.Audio;
using Discord.WebSocket;

namespace AtcBot;

public class Program
{
    private static readonly DiscordSocketClient _client = new();
    private static ulong _channelId;
    public static async Task Main()
    {
        string? channelId = Environment.GetEnvironmentVariable("channelId");
        if (string.IsNullOrEmpty(channelId))
            throw new Exception("No channelID set");
        _channelId = ulong.Parse(channelId);
        // _client = new DiscordSocketClient();
        _client.Log += Log;
        _client.Ready += Ready;
        _client.UserVoiceStateUpdated += UserVoiceStateUpdated;

        await _client.LoginAsync(TokenType.Bot, Environment.GetEnvironmentVariable("discordToken"));
        await _client.StartAsync();

        // Block the program until it is closed.
        await Task.Delay(Timeout.Infinite);
    }

    private static Task Log(LogMessage log)
    {
        Console.WriteLine(log.ToString());
        return Task.CompletedTask;
    }

    private static Task Ready()
    {
        Console.WriteLine($"{_client.CurrentUser} is connected!");
        return Task.CompletedTask;
    }

    private static Task UserVoiceStateUpdated(SocketUser user, SocketVoiceState before, SocketVoiceState after)
    {
        // Check if event is not by self (maybe not necessary) and if it concerns the relevant channel Id
        if (user.Id != _client.CurrentUser.Id && (before.VoiceChannel?.Id == _channelId || after.VoiceChannel?.Id == _channelId))
        {
            Console.WriteLine($"VoiceStateUpdate: {user} - {before.VoiceChannel?.Name ?? "null"} -> {after.VoiceChannel?.Name ?? "null"}");
            if (before.VoiceChannel == null && after.VoiceChannel != null)
            {
                Console.WriteLine($"{user} joined {after.VoiceChannel.Name}");
                _ = UserJoined(after);
            }
            else if (before.VoiceChannel != null && after.VoiceChannel == null)
            {
                Console.WriteLine($"{user} left {before.VoiceChannel.Name}");
                _ = UserLeft(before);
            }
            else if (before.VoiceChannel != null && after.VoiceChannel != null)
            {
                Console.WriteLine($"{user} switched from {before.VoiceChannel.Name} to {after.VoiceChannel.Name}");
                if (before.VoiceChannel.Id == _channelId)
                    _ = UserLeft(before);
                else
                    _ = UserJoined(after);
            }
            // else
            // {
            //     Console.WriteLine($"VoiceStateUpdate: {user} - {before.VoiceChannel?.Name ?? "null"} -> {after.VoiceChannel?.Name ?? "null"}");
            // }
        }
        return Task.CompletedTask;
    }

    private static async Task UserJoined(SocketVoiceState after)
    {
        if (after.VoiceChannel.ConnectedUsers.Count == 1)
        {
            IAudioClient audioClient = await after.VoiceChannel.ConnectAsync();
            using Process stream = CreateAudioStream();
            using AudioOutStream audioOutStream = audioClient.CreatePCMStream(AudioApplication.Mixed);
            try { await stream.StandardOutput.BaseStream.CopyToAsync(audioOutStream); }
            finally
            {
                // await audioOutStream.FlushAsync();
                // audioClient.Dispose();
                // audioOutStream.Dispose();
                stream.Kill();
                Console.WriteLine("Audio client closed");
            }
        }
        Console.WriteLine($"User joined, but connected users are {after.VoiceChannel.ConnectedUsers.Count}");
    }

    private static async Task UserLeft(SocketVoiceState before) // the user count seems to be updated even if it's the "before" state
    {
        if (before.VoiceChannel.ConnectedUsers.Count == 1)
        {
            await before.VoiceChannel.DisconnectAsync();
        }
        Console.WriteLine($"User left, but connected users are {before.VoiceChannel.ConnectedUsers.Count}");
    }

    private static Process CreateAudioStream()
    {
        Process ffmpegProcess = Process.Start(new ProcessStartInfo
        {
            FileName = "ffmpeg",
            Arguments = "-loglevel warning -f f32le -ar 8000 -ac 1 -i pipe:0 -f s16le -ar 48000 -ac 2 pipe:1",
            RedirectStandardInput = true,
            RedirectStandardOutput = true
        }) ?? throw new Exception("ffmpeg process is null");

        _ = UdpPipeAsync(ffmpegProcess.StandardInput.BaseStream);

        return ffmpegProcess;
    }

    private static async Task UdpPipeAsync(Stream output)
    {
        using UdpClient udpClient = new(2003);
        Console.WriteLine("Starting UDP client...");
        while (true) // Not sure of a better way, but seems to be disposed just fine
        {
            UdpReceiveResult udpResult = await udpClient.ReceiveAsync();
            // Console.WriteLine($"Received udp buffer {udpResult.Buffer.Length} bytes"); // The buffer is apparently 4000 bytes
            await output.WriteAsync(udpResult.Buffer.AsMemory());
        }
    }
    
    // private static async Task PipeAsync(Stream input, Stream output)
    // {
    //     byte[] buffer = new byte[512];
    //     int bytesRead;
    //     while ((bytesRead = await input.ReadAsync(buffer)) > 0)
    //     {
    //         await output.WriteAsync(buffer.AsMemory(0, bytesRead));
    //     }
    // }
}