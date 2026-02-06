/*
 * Neutron SDK - C# Authentication Library
 * =========================================
 * Use this SDK to authenticate users in your C# / .NET application.
 * 
 * Usage:
 *     var auth = new NeutronAuth();
 *     var result = await auth.LoginAsync("username", "password");
 *     
 *     if (result.Success)
 *         Console.WriteLine($"Welcome, {result.User.Username}!");
 *     else
 *         Console.WriteLine($"Error: {result.Error}");
 */

using System;
using System.Net.Http;
using System.Text;
using System.Text.Json;
using System.Threading.Tasks;
using System.Management;

namespace NeutronSDK
{
    public class NeutronAuth
    {
        // Pre-configured credentials for your application
        private readonly string ApiUrl = "{{API_URL}}";
        private readonly string AppSecret = "{{APP_SECRET}}";
        private readonly string AppName = "{{APP_NAME}}";
        private readonly string Version = "{{VERSION}}";
        
        private readonly HttpClient _client;

        public NeutronAuth()
        {
            _client = new HttpClient();
            _client.Timeout = TimeSpan.FromSeconds(10);
        }

        private string GetHWID()
        {
            try
            {
                using (var searcher = new ManagementObjectSearcher("SELECT ProcessorId FROM Win32_Processor"))
                {
                    foreach (ManagementObject obj in searcher.Get())
                    {
                        return obj["ProcessorId"]?.ToString() ?? "unknown";
                    }
                }
            }
            catch { }
            return Environment.MachineName;
        }

        public async Task<LoginResult> LoginAsync(string username, string password, string hwid = null)
        {
            hwid ??= GetHWID();
            
            var payload = new
            {
                secret = AppSecret,
                username = username,
                password = password,
                hwid = hwid
            };

            try
            {
                var json = JsonSerializer.Serialize(payload);
                var content = new StringContent(json, Encoding.UTF8, "application/json");
                
                var response = await _client.PostAsync($"{ApiUrl}/login", content);
                var responseBody = await response.Content.ReadAsStringAsync();
                
                return JsonSerializer.Deserialize<LoginResult>(responseBody);
            }
            catch (Exception ex)
            {
                return new LoginResult { Success = false, Error = ex.Message };
            }
        }

        public async Task<LicenseResult> CheckLicenseAsync(string licenseKey)
        {
            var payload = new
            {
                secret = AppSecret,
                license = licenseKey
            };

            try
            {
                var json = JsonSerializer.Serialize(payload);
                var content = new StringContent(json, Encoding.UTF8, "application/json");
                
                var response = await _client.PostAsync($"{ApiUrl}/check", content);
                var responseBody = await response.Content.ReadAsStringAsync();
                
                return JsonSerializer.Deserialize<LicenseResult>(responseBody);
            }
            catch (Exception ex)
            {
                return new LicenseResult { Success = false, Error = ex.Message };
            }
        }
    }

    public class LoginResult
    {
        public bool Success { get; set; }
        public UserInfo User { get; set; }
        public string Error { get; set; }
    }

    public class UserInfo
    {
        public string Username { get; set; }
        public string Expiry { get; set; }
        public string Hwid { get; set; }
    }

    public class LicenseResult
    {
        public bool Success { get; set; }
        public LicenseInfo License { get; set; }
        public string Error { get; set; }
    }

    public class LicenseInfo
    {
        public string Key { get; set; }
        public bool IsUsed { get; set; }
        public string CreatedAt { get; set; }
    }
}
