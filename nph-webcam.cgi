#!/usr/bin/perl5
# webcam.cgi v.1.0 <saintly@innocent.com>

# See docs in README for use and installation instructions if you
#  need them

use strict;
use vars qw($FILES $CGINAME %CONFIG @PRIV);
use vars qw(%form %cookies $User $File $ctype); 

# --- Start Config ---
# All files are relative to 'PATH' unless they start with a slash
@PRIV = ("joeuser");   # Privileged users
$FILES = {
  'PATH'   => "/usr/local/www/joecam",         # Base path
  'CAM'    => "/usr/home/joe/webcam32.jpg",    # Uploaded webcam file
  'BANNER' => "banner.gif",                    # Banner
  'USERS'  => "data/users",                    # Valid users
  'AUTH'   => "data/auth",                     # Authentication data
  'CONFIG' => "data/config",                   # Options
  'LAST'   => "data/last",                     # Last users, quickref
};
# --- End Config ---

# I see no command mode here
if(!$ENV{'REQUEST_METHOD'}) { print "Use as a CGI\n"; exit 1; }

# Init; get config vars, browser's file request,  and what the name of 
# the CGI is at the moment; then read form variables & cookies
dbmopen(%CONFIG,&filename("CONFIG"),0700);
$File = $ENV{'PATH_INFO'}; $File =~ s/(^\/|\/$)//g; 
$File = $File ? $File : "index.html";
$CGINAME = $ENV{'SCRIPT_NAME'} . "/$File";  
$CGINAME =~ s/\/$//g; $CGINAME =~ s/\/\//\//g;  # Strip double/trailing slash 
&getform(*form,*cookies); # Parse form input and cookies

# Program run for first time; setup defaults
if(!$CONFIG{'OPEN'}) { &reset_config; } 

# Process a login form if it was just submitted
if($form{'user'} && $form{'pass'}) { &do_login(@form{'user','pass'}); }

$User = &get_auth;   # See who it is...

# Switching program execution
if($CONFIG{'OPEN'} eq "PASS" && !$User) { &authform; }  # Valid users only
elsif($File eq "config") {                              # Program config mode
  if(!$User) { &authform; } else { &config; }           
} elsif($File eq "login") { &authform; }                # Explicit login
elsif($CONFIG{'OPEN'} eq "DOWN") { &goaway; }           # Program is down
elsif($File =~ /index.html?/) { &do_fullindex; }        # Pic & Visitors
elsif($File =~ /^visit.*\.html?$/) { &do_recentvis; }   # Visitors only
elsif($File =~ /^banner.gif$/) {                        # Banner image
  if( open(IMG,&filename("BANNER")) ) { 
    &webheader(200,"image/gif"); 
    while(<IMG>) { print; } close(IMG);
  } else { &webheader(200); print "$!"; }
}
elsif($File =~ /^webcam-?\d+\.jpg/) {                   # Actual cam pic
  if( open(IMG,&filename("CAM")) ) { 
    &webheader(200,"image/jpeg"); 
    while(<IMG>) { print; } close(IMG);
    &write_last;
  } else { &webheader(200); print "$!"; }
} else {                                                # Some other file
  &webheader(404); 
  print "<head><title>404 Not Found</title></head>",
    "<h1>Not Found</h1>",
    "The requested URL $CGINAME was not found on this server.<BR>",
    "<hr>$ENV{'SERVER_SIGNATURE'}";
}

dbmclose(%CONFIG); exit; 

# Show recent visitors only
sub do_recentvis {
  print<<"RECENTVIS_TOP";
<html><head><title>$CONFIG{'VIS_TITLE'}</title>
<meta html-equiv=\"pragma\" content=\"no-cache\">
<script language="JavaScript">
 <!--
  var x = $CONFIG{'RFSH'};
  function startclock() { 
     if(x<0) { self.location = self.location; }
     else { setTimeout("startclock()",1000); }
  }
 // -->
</script>
<noscript>
<meta http-equiv="refresh" content="$CONFIG{'RFSH'}">
</noscript>
<body bgcolor=#FFFFFF onload="startclock()">
RECENTVIS_TOP
  &recent_vis; print "<BR><i>Reloads every $CONFIG{'RFSH'} seconds</i>",
     "</body></html>";
}

# Displays the picture and the list of recent visitors
sub do_fullindex {
  my($bg,$text,$tm,$T,$B); if($CONFIG{'COLR'} == 0) { 
    ($bg,$text,$tm) = ("000000","FFFFFF","202020");  # White on black
  } elsif($CONFIG{'COLR'} == 1) { 
    ($bg,$text,$tm) = ("FFFFFF","000000","EFEFEF");  # Black on white
  }
  $CGINAME =~ s/(.*)\/.+/$1/; # Strip trailing filename
  if($CONFIG{'SH_TITLE'}) {  $T = "<h2>$CONFIG{'TITLE'}<hr></h2>\n"; }
  if($CONFIG{'SH_BANNER'}) { 
    $B="<tr><td bgcolor=101040><img src=\"$CGINAME/banner.gif\"></td></tr>\n";
  }

  my($L1,$L1a,$L2a,$L2b,$L3);  # Layout options
  if($CONFIG{'LAYT'} == 0) {  # Side-by-side
    $L1  = "<table border=0 cellpadding=5 cellspacing=5><tr><td valign=top>\n";
    $L2b = "</td><td valign=top>\n";
    $L3  =  "</td></tr></table>\n";
  } elsif($CONFIG{'LAYT'} == 3) {  # Side-by-side
    $L1  = "</center><table border=0 cellpadding=5 cellspacing=5>" .
           "<tr><td valign=top>\n";
    $L2a = "</td><td valign=top>\n";
    $L3  =  "</td></tr></table>\n";
  } elsif($CONFIG{'LAYT'} == 2) { 
    $L1 = "</center>"; $L1a = "<BR><BR><center>";
  } else { $L2a = "<BR><BR></center>"; }
  
  # Either the picture link, or an "Image Unavailable sign" if it's gone  
  # timestamp appended to filename to fix brainless browsers that might
  # ignore the BIG FREAKING *NO-CACHE* PRAGMA (*cough* IE *cough*)
  my($t) = +(stat(&filename('CAM')))[9]; if($t) { $t =
   "<img src=\"$CGINAME/webcam-$t\.jpg\" height=240 width=320 alt=\"Loading\">" 
  . "</td></tr><tr><td bgcolor=#$tm align=center><b>" . localtime($t) . "</b>";
  } else { $t = "Webcam unavailable!"; }

  &webheader(200); print <<"END_FULLINDEX_TOP"; 
<html>
<head>
<title>$CONFIG{'TITLE'}</title>
<meta html-equiv=\"pragma\" content=\"no-cache\">
<script language="JavaScript">
 <!--
  var x = $CONFIG{'RFSH'};
  function startclock() { 
     document.form1.clock.value = x--;
     if(x<0) { self.location = self.location; }
     else { setTimeout("startclock()",1000); }
  }
 // -->
</script>
<noscript>
<meta http-equiv="refresh" content="$CONFIG{'RFSH'}">
</noscript>
</head>
<body bgcolor=#$bg text="#$text" onload="startclock()">
$T<center>$L1
END_FULLINDEX_TOP
  if($CONFIG{'LAYT'} == 2 || $CONFIG{'LAYT'} == 3) {  
    &recent_vis;  # Pic on bottom or right
  }
  print <<"END_FULLINDEX_BOT"; 
$L1a$L2a
  <table border=1>$B
  <tr><td>$t</td></tr></table>
<form name="form1">
Page will refresh in 
<input type=text name="clock" size=3 value="$CONFIG{'RFSH'}"> seconds $L2b
END_FULLINDEX_BOT
  if($CONFIG{'LAYT'} == 0 || $CONFIG{'LAYT'} == 1) {  
    &recent_vis;  # Pic on top or left
  }
  print "$L3</form></body></html>";
}

# Displays the list of recent visitors to the pic only
sub recent_vis {
  my(@users,$user) = &get_last; 
  if(@users) { 
    print "<B>Recent visitors:</B><BR>";
    foreach $user (@users) { 
      my($time,$ip,$name,$user) = split(/,/,$user);
      $time = localtime($time + 60*60*2) . " CST"; 
      $user = $user ? "$user" : "Someone";
      if(!$name) { $name = $ip; }
      print "$user from $name on $time<BR>\n";
    }
  }
}

# Displays a user for editing (such as it is) -
#  allows resetting the password, disallowing the user and deleting the user
sub useredit {
  my($user) = $form{'edit'};
  my(%USER); if( dbmopen(%USER,&filename("USERS"),0700) ) {
    if($form{'submit'} eq "Delete User") {  
      delete $USER{$user}; delete $form{'edit'}; &config;
    } elsif($form{'submit'}) { 
      my($pass,$last,$ct,@rest,$allow,$time,$name) = split(/\xFF/,$USER{$user});
      if($form{'pass'}) { $pass = crypt($form{'pass'},"Zz"); }
      if(!$form{'allow'}) {
         if($pass ne "*") { push(@rest,$pass); $pass = "*"; }
      } elsif($pass eq "*") { $pass = pop(@rest); }
      $USER{$user} = join("\xFF",$pass,$last,$ct,@rest);
      delete $form{'edit'}; &config;
    } else {
      my($pass,$last,$ct,@rest,$allow,$time,$name) = split(/\xFF/,$USER{$user});
      if($pass eq "*") { $pass = pop(@rest); $allow = ""; } 
      else { $allow = " checked"; }
      ($time,$last) = split(/:/,$last); $time = localtime($time);
      $name = &gethostname($last);
      print<<"END_USERDISPLAY";
<html>
<head>
<title>$CONFIG{'TITLE'}</title>
<meta html-equiv=\"pragma\" content=\"no-cache\">
</head>
<body bgcolor=#FFFFFF>
<h2>Editing user: $user<hr></h2>
<form action=$CGINAME method=POST>
<input type=hidden name=edit value=\"$user\">
<table border=0>
<tr><td bgcolor=EFEFEF>Allow this user to visit the cam</td>
<td><input type=checkbox name=allow$allow></td>
</td></tr><tr><td valign=top bgcolor=EFEFEF>Visit count:</td>
<td>$ct</td></tr><tr><td valign=top bgcolor=EFEFEF>Last visited:</td>
<td>On $time<BR>From $name &nbsp; ($last)
</td></tr><tr><td bgcolor=EFEFEF>
Assign new password:</td><td><input type=text name=pass size=20></td></tr>
<tr><td colspan=2>
  <input type=submit name=submit value="Change">
  <input type=submit name=submit value="Delete User"></td></tr>
</table></form>
END_USERDISPLAY
    }
    dbmclose(%USER);  
  } else { 
    print "Can't find that user!<BR>\n";
  }
}

# Set/Get Config & Status
sub config { 
  my($p,$u); foreach $u (@PRIV) { if($u eq $User) { $p = $u; } }
  if(!$p) { 
    &webheader(403);
    print "<head><title>403 Forbidden</title></head>",
    "<h1>Forbidden</h1>",
    "The requested URL $CGINAME could not be displayed.<BR>",
    "<hr>$ENV{'SERVER_SIGNATURE'}";
  }
  &webheader(200); 
  my($lk) = $CGINAME; $lk =~ s/\/[^\/]+$//;
  $lk = "<a href=\"$lk\">(Back to page)</a>";
  if($form{'edit'}) { &useredit; return; }
  elsif($form{'OPEN'}) { 
    my($key); foreach $key ('OPEN','TIME','RFSH','TITLE','VIS_TITLE',
      'COLR','LAYT','SH_TITLE','SH_BANNER') {
      $CONFIG{$key} = $form{$key};
    }
    my(%USER); if( dbmopen(%USER,&filename("USERS"),0700) ) {
      foreach $key (keys %USER) {
        my($pass,@rest) = split(/\xFF/,$USER{$key});
        if($form{"allow_$key"}) { 
          if($pass eq "*") { $pass = pop(@rest); }
        } elsif($pass ne "*") { push(@rest,$pass); $pass = "*"; }
        $USER{$key} = join("\xFF",$pass,@rest); 
      }
      if($form{'newname'} && $form{'newpass'}) { 
        $form{'newpass'} = crypt($form{'newpass'},"Zz"); 
        &userpass($form{'newname'},$form{'newpass'});
      }
    }
    dbmclose(%USER);
  }
  my(%otyp,%col,%lay,$Ti,$Ba,$T,$R); 
  $otyp{$CONFIG{'OPEN'}} = " selected"; $col{$CONFIG{'COLR'}} = " selected";
  $lay{$CONFIG{'LAYT'}} = " selected"; 
  $Ti = ($CONFIG{'SH_TITLE'}) ? " checked" : ""; 
  $Ba = ($CONFIG{'SH_BANNER'}) ? " checked" : ""; 
  $T = &opts($CONFIG{'TIME'},30,60,300,600,1800,3600,10800,21600,43200,86400);
  $R = &opts($CONFIG{'RFSH'},30,60,120,180,240,300,600);

  print <<"END_CONFIG";
<html>
<head>
<title>$CONFIG{'TITLE'}</title>
<meta html-equiv=\"pragma\" content=\"no-cache\">
</head>
<body bgcolor=#FFFFFF>
<h2>$CONFIG{'TITLE'} Configuration<hr></h2>$lk<BR>
<form action=$CGINAME method=POST>
<table border=0>
<tr>
  <td bgcolor=#EFEFEF>Accessibility level for the cam:</td>
  <td><select name="OPEN">
<option value="DOWN"$otyp{'DOWN'}>No-one</option>
<option value="PASS"$otyp{'PASS'}>Only users with passwords</option>
<option value="PUBL"$otyp{'PUBL'}>Anyone</option>
</select></td>
</tr><tr>
  <td bgcolor=#EFEFEF>Length of time for Recent Visitors:</td>
  <td><select name="TIME">$T</select></td>
</tr><tr>
  <td bgcolor=#EFEFEF>How often to refresh the page:</td>
  <td><select name="RFSH">$R</select></td>
</tr><tr>
  <td bgcolor=#EFEFEF>Title for the picture page:</td>
  <td><input type=text name=TITLE value="$CONFIG{'TITLE'}" size=40></td>
</tr><tr>
  <td bgcolor=#EFEFEF valign=top>Picture page config:</td>
  <td>
Colors: <select name=COLR>
<option value=0$col{0}>White text on Black</option>
<option value=1$col{1}>Black text on White</option>
</select><BR>
Layout: <select name=LAYT>
<option value=0$lay{0}>Pic on left</option>
<option value=1$lay{1}>Pic on top</option>
<option value=2$lay{2}>Pic on bottom</option>
<option value=3$lay{3}>Pic on right</option>
</select><BR>
<input type=checkbox name="SH_TITLE"$Ti> Show title text<BR>
<input type=checkbox name="SH_BANNER"$Ba> Show banner image on top of photo<BR>
</td></tr><tr>
  <td bgcolor=#EFEFEF>Title for the recent-visitors page:</td>
  <td><input type=text name=VIS_TITLE value="$CONFIG{'VIS_TITLE'}" size=40></td>
</tr>
<tr><th colspan=2><input type=submit value=\"Change Settings\"></th></tr>
</tr><tr><td colspan=2><BR></td></tr>
<tr><th colspan=2 bgcolor=#EFEFEF valign=top>Users:</th></tr>
<tr><td colspan=2>
Create new user with name <input type=text name=newname size=13>
and password <input type=text name=newpass size=12>
<input type=submit value="Go!"></td>
</tr><tr><td colspan=2><BR></td></tr>
<tr><td colspan=2>
END_CONFIG
  my(%USER); if( dbmopen(%USER,&filename("USERS"),0700) ) {
    print "<table border=0 cellpadding=2 cellspacing=2>",
     "<tr><th>Allow</th><th>Name</th>",
     "<th align=center>Last Visit</th><th>Visits</th></tr>";
    my($user); foreach $user (sort keys %USER) {
      my($pass,$last,$ct,@rest,$allow,$time) = split(/\xFF/,$USER{$user});
      if($pass eq "*") { $pass = pop(@rest); $allow = ""; } 
      else { $allow = " checked"; }

      ($time,$last) = split(/:/,$last); $time = localtime($time);
      $last = &gethostname($last);
      print "<tr>",
      "<td align=center><input type=checkbox name=\"allow_$user\"$allow></td>",
      "<td><a href=\"$CGINAME?edit=",&urlencode($user),"\">$user</a></td>",
      "<td> $time from $last </td>",
      "<td align=center>$ct</td></tr>";
    }
    print "</table>";
    dbmclose(%USER); 
  }
  print "<tr><th colspan=2><BR></th></tr>",
   "<tr><th colspan=2><input type=submit value=\"Update\"></th></tr>",
   "</table></form>";
}

# Build option list for a <select> pull-down from list of seconds, 
# see it in action on the config menu 
sub opts { 
  my($comp,@opts,$x,$rv) = @_; foreach $x (@opts) { 
    $rv .= "<option value=\"$x\"" .  (($comp == $x) ? " selected" : "") .  ">";
    my(@timing,$t,@tostr) = ("day:86400","hour:3600","minute:60","second:1");
    foreach $t (@timing) { 
      my($id,$secs) = split(/:/,$t); if($x > $secs) { 
        my($rest) = $x % $secs; $x -= $rest; $x /= $secs;
        push(@tostr,"$x $id" . (($x > 1) ? "s" : "")); $x = $rest;
      }
    }
    $rv .= join(" ",@tostr) . "</option>\n"; 
  }
  return $rv;
}

# Gets the host by IP address in string form, if possible
sub gethostname {
  my($ip) = @_; return unless $ip =~ /^\d+\.\d+\.\d+\.\d+$/;
  my($rv) = scalar(gethostbyaddr(pack('C4',split(/\./,$ip)),2));
  return $rv ? "$rv" : "$ip";
}

# Print go-away message
sub goaway {
  &webheader(200); print<<"END_GOAWAY";
<html>
 <head>
  <title>$CONFIG{'TITLE'}</title>
  <meta html-equiv=\"pragma\" content=\"no-cache\">
 </head>
 <body bgcolor=#FFFFFF> 
    <p>Sorry! $CONFIG{'TITLE'} is closed right now!  Come back later.</p>
 </body>
</html>
END_GOAWAY
}

# Print login form
sub authform {
  $CGINAME =~ s/\/login$//;
  &webheader(200); print<<"END_GETAUTH";
<html>
 <head>
  <title>$CONFIG{'TITLE'}</title>
  <meta html-equiv=\"pragma\" content=\"no-cache\">
 </head>
 <body bgcolor=#FFFFFF>
  <h2>You need to log-in to $CONFIG{'TITLE'}<hr></h2>
  <form action=$CGINAME method=POST>
    User: <input type=text name=user size=10><BR>
    Pass: <input type=password name=pass size=10><BR>
  <input type=submit value="Login">
  </form>
 </body>
</html>
END_GETAUTH
}

# Update the 'last visitors' list when a user views the pic
sub write_last {
  my($ip,$time,$key) = ($ENV{'REMOTE_ADDR'},time);
  my($name) = gethostname($ip);
  my(%LAST); dbmopen(%LAST,&filename("LAST"),0700) || return 0;
  my(@keys) = sort keys %LAST;
  while( @keys && ($time - ($key = shift(@keys))) > $CONFIG{'TIME'} ) {
    delete $LAST{$key};
  }
  unshift(@keys,$key) if $key; while($key = shift(@keys)) {
    my(@hits,$hit,$f); foreach $hit (split(/\xFF/,$LAST{$key})) {
      if( +(split(/,/,$hit,2))[0] eq $ip) { $f++; } else { push(@hits,$hit); }
    }
    if($f) { 
      if(@hits) { $LAST{$key} = join("\xFF",@hits); }
      else { delete $LAST{$key}; }
    }
  }
  $LAST{$time} .= ($LAST{$time} ? "\xFF" : "") . join(",",$ip,$name,$User);
  dbmclose(%LAST);
}

# Return a list of the last people to visit
sub get_last {
  my(@ret,$key) = ();
  my(%LAST); dbmopen(%LAST,&filename("LAST"),undef) || return @ret;
  foreach $key (reverse sort keys %LAST) { 
    push(@ret,join(",",$key,$LAST{$key}));
  }
  dbmclose(%LAST); return @ret;
}

# Get login, set cookie if authorized
sub do_login {
  my($user,$pass) = @_; return if !($user && $pass && $ENV{'REMOTE_ADDR'}); 
  my($auth) = $ENV{'UNIQUE_ID'}; $pass = crypt($pass,"Zz");
  # my($chk) = &userpass($user,$pass);
  if($pass eq &userpass($user)) { 
     my(%AUTH); dbmopen(%AUTH,&filename("AUTH"),0700) || return 0;
     my($last) = $AUTH{$user}; kill $AUTH{$last};
     $AUTH{$user} = $auth; $AUTH{$auth} = "$ENV{'REMOTE_ADDR'}\xFF$user";
     &webheader(200,"","Set-Cookie: lesliecam-auth=$auth");
     $cookies{'lesliecam-auth'} = $auth;
     dbmclose(%AUTH);
  }
  else { &webheader(200); print "\n<B><I>Bad Login</I></B><BR>"; }
}

# Set/get password by username
sub userpass {
  my($user,$pass) = @_; return 0 if !$user;
  my(%USER); dbmopen(%USER,&filename("USERS"),0700) || return 0;
  my($rv,@rest) = split(/\xFF/,$USER{$user});
  if(defined $pass) { $USER{$user} = join("\xFF",$pass,@rest); }
  dbmclose(%USER); return $rv;
}

# Return connecting user; authorization by cookie
sub get_auth {
  if(!$cookies{'lesliecam-auth'}) { return 0; }
  else { 
    my(%AUTH); dbmopen(%AUTH,&filename("AUTH"),undef) || return 0;
    my($ip,$user) = split(/\xFF/,$AUTH{$cookies{'lesliecam-auth'}});
    dbmclose(%AUTH); return 0 if ($ip ne $ENV{'REMOTE_ADDR'});
    my(%USER); dbmopen(%USER,&filename("USERS"),0700) || return $user;
    my($pass,$last,$ct,@rest) = split(/\xFF/,$USER{$user});
    $last = join(":",time,$ENV{'REMOTE_ADDR'}); $ct++;
    $USER{$user} = join("\xFF",$pass,$last,$ct,@rest); 
    dbmclose(%USER); return $user;
  }
}

# Get a filename out of the FILES hash
sub filename {
  my($file) = @_; 
  if(!$$FILES{$file}) { return ""; }
  elsif($$FILES{$file} =~ /^\//) { return $$FILES{$file}; }
  else { 
     return $$FILES{'PATH'} . (($$FILES{'PATH'} =~ /\/$/) ? "" : "/") . 
            $$FILES{$file};
  }
}

# Prints the HTTP response header and content type
sub webheader {
  return "" if $ctype;
  my($code,$mime,@headers) = @_; 
  $code = 200 unless($code =~ /^\d+$/);
  $mime = "text/html" unless($mime =~ /^[a-z0-9]+\/[a-z0-9]+$/);
  print "HTTP/1.1 $code\nContent-type: $mime\n",join("\n",@headers),
     (@headers ? "\n\n" : "\n");
  $ctype = $mime;
}

# Reset all config options (runs once when the CGI is first run)
sub reset_config {
  $CONFIG{'TIME'} = 600;    # TTL on Recent visitors
  $CONFIG{'TITLE'} = "The Amazing JoeCam!";
  $CONFIG{'VIS_TITLE'} = "Recent Visitors to The Amazing JoeCam!";
  $CONFIG{'OPEN'} = "PUBL"; # Default security level
  $CONFIG{'RFSH'} = "30";   # Default page refresh time
  $CONFIG{'COLR'} = "0";    # White on black page colors
  $CONFIG{'LAYT'} = "1";    # Pic on the left, visitors on the right
  $CONFIG{'SH_TITLE'} = 1;  # Display the title
  $CONFIG{'SH_BANNER'} = 0; # Don't display the banner

  &userpass($PRIV[0],crypt($PRIV[0],"Zz"));  # Create first user
}

# Parses data from a submitted form and places it
# in a given associative array.  Syntax:
#    &getform(*input,*cookie);   
#    Places form data in %input, cookies in %cookie
# Also parses cookie data in separate hash
sub getform {
 my($query,$ipair,$var,$val); 
 use vars qw(*hash *cookie_hash);
 local(*hash,*cookie_hash) = @_;
 
 if($#_) {
   foreach $ipair (split(/;\s?/,$ENV{'HTTP_COOKIE'})) {
     ($var, $val) = split(/=/, $ipair,2);
     if(defined $cookie_hash{$var}) { $cookie_hash{$var} .= "," . $val; }
     else { $cookie_hash{$var} = $val; }
   }
 }

 if($ENV{'REQUEST_METHOD'} eq "GET") {
   $query = $ENV{'QUERY_STRING'};
 } else { read(STDIN,$query, $ENV{'CONTENT_LENGTH'}); }

 foreach $ipair (split(/&/,$query)) {
    ($var,$val) = split(/=/,$ipair,2);
 
    $val =~ tr/+/ /;
    while($val =~ /(%([0-F]{2}))/) {
 	my($find,$rep) = ($1,chr(hex($2)));
        $val =~ s/$find/$rep/g;
    }
    
    if(defined $hash{$var}) { $hash{$var} .= "," . $val; }
    else { $hash{$var} = $val; }
 }
}

# URL-encode a string
sub urlencode {
  my($x) = @_;   
  $x =~ s/([^A-Za-z0-9&~\-\.\/\=\?\_])/sprintf("%%%X",ord($1))/ge; 
  $x =~ s/ /+/g;
  return $x;
}
